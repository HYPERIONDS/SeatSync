# Architecture plan

SeatSync is a modular monolith: modules own route, service, and schema code, while sharing one process and one PostgreSQL database. This keeps deployment and debugging appropriate for a small team while preserving boundaries that can be extracted only if scale later justifies it.

```mermaid
flowchart LR
  UI["React + TypeScript UI"] --> API["FastAPI modular monolith"]
  API --> DB[(PostgreSQL)]
  API --> R[(Redis holds + Celery broker)]
  API --> W["Celery worker"]
  W --> DB
  W --> MH["MailHog / console SMTP"]
```

## Module responsibilities

| Module | Responsibility |
|---|---|
| auth/users | registration, password verification, JWTs, roles |
| venues | organizer-owned venues, layout validation, seat generation |
| events/shows | catalogue, show scheduling, prices, discovery |
| seat_holds | atomic Redis holds and derived availability |
| bookings/payments | transaction, uniqueness, idempotency, lifecycle |
| notifications | transactional notification records and retried delivery |
| audit | append-only security/business history |
| reporting | organizer metrics and asynchronous attendee CSV |

## Concurrency sequence

```mermaid
sequenceDiagram
  participant C as Customer
  participant A as FastAPI
  participant R as Redis
  participant P as PostgreSQL
  C->>A: POST /holds (seat IDs)
  A->>R: atomic Lua check-and-set
  R-->>A: hold ID + TTL or conflict
  C->>A: POST /bookings/confirm + idempotency key
  A->>R: validate hold owner and expiry
  A->>P: begin transaction
  A->>P: insert pending booking/payment
  A->>P: insert confirmed booking seats
  Note over P: partial unique index is final guard
  A->>P: mark confirmed + store idempotent response
  P-->>A: commit all rows
  A->>R: release hold
  A-->>C: original or replayed response
```

## Failure handling

- Redis conflict: reject before payment simulation.
- Redis outage: new holds fail closed; the database constraint still protects confirmations already in flight.
- Partial conflict: one transaction rolls back every selected seat.
- Payment failure/timeout: retain the attempt, expire the booking, release the hold.
- Notification failure: Celery retries the same notification row; `deduplication_key` and `sent_at` prevent duplicates.

