import json
import time
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError, ResponseError, WatchError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.bookings.models import BookingSeat, BookingSeatStatus
from app.core.config import get_settings
from app.core.time import as_utc, utcnow
from app.seat_holds.schemas import HoldCreate
from app.shows.models import Show, ShowStatus
from app.users.models import User
from app.venues.models import Seat

CREATE_HOLD_LUA = """
local seat_count = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local expiry = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])
local hold_id = ARGV[5]
local payload = ARGV[6]
local user_key = KEYS[seat_count + 1]
local hold_key = KEYS[seat_count + 2]
redis.call('ZREMRANGEBYSCORE', user_key, '-inf', now)
if redis.call('ZCARD', user_key) + seat_count > 5 then return -1 end
for i = 1, seat_count do
  if redis.call('EXISTS', KEYS[i]) == 1 then return -2 end
end
for i = 1, seat_count do
  redis.call('SET', KEYS[i], hold_id, 'EX', ttl)
  redis.call('ZADD', user_key, expiry, hold_id .. ':' .. i)
end
redis.call('EXPIRE', user_key, ttl + 1)
redis.call('SET', hold_key, payload, 'EX', ttl)
return 1
"""

RELEASE_HOLD_LUA = """
local seat_count = tonumber(ARGV[1])
local hold_id = ARGV[2]
local user_key = KEYS[seat_count + 1]
local hold_key = KEYS[seat_count + 2]
for i = 1, seat_count do
  if redis.call('GET', KEYS[i]) == hold_id then redis.call('DEL', KEYS[i]) end
  redis.call('ZREM', user_key, hold_id .. ':' .. i)
end
redis.call('DEL', hold_key)
return 1
"""


def hold_key(hold_id: str | UUID) -> str:
    return f"hold:{hold_id}"


def seat_key(show_id: str | UUID, seat_id: str | UUID) -> str:
    return f"seat:{show_id}:{seat_id}"


def user_holds_key(user_id: str | UUID) -> str:
    return f"user-holds:{user_id}"


def _watch_create(redis: Redis, keys: list[str], args: list) -> int:
    """Atomic WATCH fallback for test Redis implementations without Lua."""
    seat_count, now, expiry, ttl, hold_id, payload = args
    seat_keys = keys[:seat_count]
    user_key, record_key = keys[-2:]
    for _ in range(10):
        try:
            with redis.pipeline() as pipe:
                pipe.watch(user_key, *seat_keys)
                pipe.zremrangebyscore(user_key, "-inf", now)
                if pipe.zcard(user_key) + seat_count > 5:
                    pipe.unwatch()
                    return -1
                if any(pipe.mget(seat_keys)):
                    pipe.unwatch()
                    return -2
                pipe.multi()
                for index, key in enumerate(seat_keys, 1):
                    pipe.set(key, hold_id, ex=ttl)
                    pipe.zadd(user_key, {f"{hold_id}:{index}": expiry})
                pipe.expire(user_key, ttl + 1)
                pipe.set(record_key, payload, ex=ttl)
                pipe.execute()
                return 1
        except WatchError:
            continue
    raise RedisError("Could not serialize hold after retries")


def create_hold(
    db: Session, redis: Redis, customer: User, data: HoldCreate, ttl_seconds: int | None = None
) -> dict:
    show = db.get(Show, data.show_id)
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    if show.status != ShowStatus.SCHEDULED or as_utc(show.starts_at) <= utcnow():
        raise HTTPException(status_code=409, detail="Past or cancelled shows cannot be booked")
    seats = db.scalars(
        select(Seat).where(Seat.id.in_(data.seat_ids), Seat.venue_id == show.venue_id)
    ).all()
    if len(seats) != len(data.seat_ids):
        raise HTTPException(status_code=422, detail="All seats must belong to the show venue")
    booked = db.scalar(
        select(func.count(BookingSeat.id)).where(
            BookingSeat.show_id == show.id,
            BookingSeat.seat_id.in_(data.seat_ids),
            BookingSeat.status == BookingSeatStatus.CONFIRMED,
        )
    )
    if booked:
        raise HTTPException(status_code=409, detail="One or more seats are already booked")
    ttl = ttl_seconds or get_settings().hold_ttl_seconds
    hold_id = uuid4()
    now = utcnow()
    expires_at = now + timedelta(seconds=ttl)
    payload = {
        "hold_id": str(hold_id),
        "customer_id": str(customer.id),
        "show_id": str(show.id),
        "seat_ids": [str(seat_id) for seat_id in data.seat_ids],
        "expires_at": expires_at.isoformat(),
    }
    keys = [seat_key(show.id, seat_id) for seat_id in data.seat_ids]
    keys.extend([user_holds_key(customer.id), hold_key(hold_id)])
    args = [
        len(data.seat_ids),
        int(time.time()),
        int(time.time()) + ttl,
        ttl,
        str(hold_id),
        json.dumps(payload),
    ]
    try:
        try:
            result = redis.eval(CREATE_HOLD_LUA, len(keys), *keys, *args)
        except ResponseError as exc:
            if "unknown command" not in str(exc).lower():
                raise
            result = _watch_create(redis, keys, args)
    except RedisError as exc:
        raise HTTPException(
            status_code=503, detail="Seat holding is temporarily unavailable"
        ) from exc
    if result == -1:
        raise HTTPException(status_code=409, detail="A customer may hold at most five seats")
    if result == -2:
        raise HTTPException(status_code=409, detail="One or more seats are already held")
    return payload


def read_hold(redis: Redis, hold_id: str | UUID) -> dict | None:
    raw = redis.get(hold_key(hold_id))
    return json.loads(raw) if raw else None


def release_hold(redis: Redis, customer: User, hold_id: UUID) -> None:
    payload = read_hold(redis, hold_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Hold not found or expired")
    if payload["customer_id"] != str(customer.id):
        raise HTTPException(status_code=403, detail="This hold belongs to another customer")
    keys = [seat_key(payload["show_id"], seat_id) for seat_id in payload["seat_ids"]]
    keys.extend([user_holds_key(customer.id), hold_key(hold_id)])
    args = [len(payload["seat_ids"]), str(hold_id)]
    try:
        redis.eval(RELEASE_HOLD_LUA, len(keys), *keys, *args)
    except ResponseError as exc:
        if "unknown command" not in str(exc).lower():
            raise
        with redis.pipeline() as pipe:
            for index, key in enumerate(keys[: args[0]], 1):
                if redis.get(key) == str(hold_id):
                    pipe.delete(key)
                pipe.zrem(keys[-2], f"{hold_id}:{index}")
            pipe.delete(keys[-1])
            pipe.execute()
