import { CalendarDays, LogOut, TicketCheck } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function Layout() {
  const { user, logout } = useAuth();
  return <div className="min-h-screen bg-ink text-cream">
    <div className="border-b border-white/10 bg-ink/90 backdrop-blur sticky top-0 z-30">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
        <Link to="/" className="flex items-center gap-2 font-display text-2xl"><TicketCheck className="text-mint" /> SeatSync</Link>
        <nav className="flex items-center gap-4 text-sm text-white/70">
          <NavLink className="hover:text-mint" to="/">Discover</NavLink>
          {user?.role === "CUSTOMER" && <NavLink className="hover:text-mint" to="/bookings">My bookings</NavLink>}
          {(user?.role === "ORGANIZER" || user?.role === "ADMIN") && <NavLink className="hover:text-mint" to="/organizer">Organizer</NavLink>}
          {user ? <button onClick={logout} className="flex items-center gap-1 rounded-full border border-white/15 px-3 py-2 hover:border-coral hover:text-coral"><LogOut size={15} /> Sign out</button> : <Link className="rounded-full bg-mint px-4 py-2 font-semibold text-ink" to="/login">Sign in</Link>}
        </nav>
      </header>
    </div>
    <main className="mx-auto max-w-7xl px-5 py-10"><Outlet /></main>
    <footer className="mx-auto mt-20 flex max-w-7xl items-center justify-between border-t border-white/10 px-5 py-8 text-sm text-white/45"><span>SeatSync engineering portfolio</span><span className="flex gap-2"><CalendarDays size={16} /> Simulated payments only — no real money</span></footer>
  </div>;
}
