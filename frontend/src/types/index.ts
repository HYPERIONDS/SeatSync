export type Role = "CUSTOMER" | "ORGANIZER" | "ADMIN";
export type SeatCategory = "STANDARD" | "PREMIUM" | "VIP";
export type SeatState = "AVAILABLE" | "HELD" | "BOOKED";

export interface User { id: string; email: string; full_name: string; role: Role; }
export interface Tokens { access_token: string; refresh_token: string; user: User; }
export interface EventCard { id: string; title: string; description: string; category: string; image_url?: string; next_show: string; }
export interface Price { category: SeatCategory; amount_minor: number; }
export interface Show { id: string; starts_at: string; ends_at: string; status: string; currency: string; prices: Price[]; venue: { id: string; name: string; city: string; address: string; }; }
export interface EventDetails extends Omit<EventCard, "next_show"> { shows: Show[]; }
export interface Seat { id: string; identifier: string; section: string; row: string; number: number; category: SeatCategory; state: SeatState; }
export interface BookingSeat { seat_id: string; category: SeatCategory; price_minor: number; status: string; }
export interface Booking { id: string; show_id: string; status: "PENDING" | "CONFIRMED" | "CANCELLED" | "EXPIRED"; total_minor: number; currency: string; created_at: string; confirmed_at?: string; cancelled_at?: string; seats: BookingSeat[]; }
