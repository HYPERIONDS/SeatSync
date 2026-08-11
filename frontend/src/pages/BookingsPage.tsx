import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Notice } from "../components/Notice";
import type { Booking } from "../types";
import { errorMessage, money } from "../utils";

export function BookingsPage() {
  const [items, setItems] = useState<Booking[]>([]); const [notice, setNotice] = useState("");
  const load = () => api.get<Booking[]>("/bookings/me").then(({ data }) => setItems(data)).catch((e) => setNotice(errorMessage(e)));
  useEffect(() => { void load(); }, []);
  const cancel = async (id: string) => { try { await api.post(`/bookings/${id}/cancel`); setNotice("Booking cancelled and a simulated refund was recorded."); load(); } catch (e) { setNotice(errorMessage(e)); } };
  return <><div className="mb-10"><p className="text-sm font-bold uppercase tracking-[.3em] text-mint">History preserved</p><h1 className="mt-3 font-display text-6xl">My bookings</h1></div>{notice && <Notice message={notice} />}
    <div className="mt-6 space-y-4">{items.map((booking) => <article key={booking.id} className="flex flex-col justify-between gap-5 rounded-2xl border border-white/10 bg-panel p-6 md:flex-row md:items-center"><div><span className={`rounded-full px-3 py-1 text-xs font-bold ${booking.status === "CONFIRMED" ? "bg-mint/10 text-mint" : "bg-white/5 text-white/50"}`}>{booking.status}</span><h2 className="mt-3 font-mono text-sm text-white/65">{booking.id}</h2><p className="mt-2 text-sm text-white/40">{booking.seats.length} seat(s) · created {new Date(booking.created_at).toLocaleString()}</p></div><div className="text-right"><strong className="text-xl">{money(booking.total_minor, booking.currency)}</strong><p className="text-xs text-white/35">simulated payment</p>{booking.status === "CONFIRMED" && <button onClick={() => void cancel(booking.id)} className="mt-3 rounded-lg border border-coral/40 px-3 py-2 text-sm text-coral hover:bg-coral/10">Cancel booking</button>}</div></article>)}</div>{items.length === 0 && <p className="rounded-2xl border border-dashed border-white/15 p-12 text-center text-white/40">No bookings yet.</p>}</>;
}
