# Entity relationship diagram

```mermaid
erDiagram
  USER ||--o{ VENUE : owns
  USER ||--o{ EVENT : organizes
  USER ||--o{ BOOKING : places
  USER ||--o{ REFRESH_TOKEN : has
  VENUE ||--o{ VENUE_SECTION : contains
  VENUE_SECTION ||--o{ SEAT : contains
  EVENT ||--o{ SHOW : schedules
  VENUE ||--o{ SHOW : hosts
  SHOW ||--o{ SHOW_PRICE : prices
  SHOW ||--o{ BOOKING : receives
  BOOKING ||--|{ BOOKING_SEAT : contains
  SEAT ||--o{ BOOKING_SEAT : referenced_by
  BOOKING ||--o{ PAYMENT_ATTEMPT : attempts
  BOOKING ||--o{ REFUND : refunds
  USER ||--o{ IDEMPOTENCY_RECORD : submits
  USER ||--o{ AUDIT_EVENT : acts
  BOOKING ||--o{ NOTIFICATION : triggers
```

The important constraints are `(venue_id, identifier)` on seats, `(show_id, category)` on prices, `(user_id, key)` on idempotency records, and a PostgreSQL partial unique index on `(show_id, seat_id)` where a booking-seat row is `CONFIRMED`.

