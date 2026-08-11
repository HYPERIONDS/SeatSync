# API catalogue

All routes are under `/api/v1`. Swagger is available at `/docs`.

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register` | Public | Register customer/organizer |
| POST | `/auth/login` | Public | Access and refresh JWTs |
| POST | `/auth/refresh` | Public | Rotate refresh token |
| GET | `/users/me` | Authenticated | Current profile |
| POST | `/venues` | Organizer/Admin | Create venue and generated seats |
| GET | `/venues/{id}` | Public | Venue layout |
| POST | `/events` | Organizer/Admin | Create event |
| POST | `/events/{id}/shows` | Owner/Admin | Create non-overlapping show and prices |
| GET | `/events` | Public | Upcoming events; city/date/category/sort/page filters |
| GET | `/events/{id}` | Public | Event, shows, and venues |
| GET | `/shows/{id}/seats` | Public | Derived AVAILABLE/HELD/BOOKED map |
| POST | `/holds` | Customer | Atomically hold up to five seats |
| DELETE | `/holds/{id}` | Hold owner | Release hold |
| POST | `/bookings/confirm` | Customer | Simulated payment and transactional confirmation |
| GET | `/bookings/me` | Customer | Booking history |
| POST | `/bookings/{id}/cancel` | Booking owner/Admin | Cancel and record simulated refund |
| GET | `/organizer/dashboard` | Organizer/Admin | Scoped metrics |
| POST | `/organizer/shows/{id}/attendees/export` | Show owner/Admin | Queue CSV export |
| GET | `/organizer/exports/{id}` | Export owner/Admin | Download completed CSV |
| GET | `/audit` | Admin | Paginated audit history |
| PATCH | `/admin/users/{id}/role` | Admin | Change role with audit record |

