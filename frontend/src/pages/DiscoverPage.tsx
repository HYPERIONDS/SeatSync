import { ArrowRight, MapPin } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Notice } from "../components/Notice";
import type { EventCard } from "../types";
import { errorMessage } from "../utils";

export function DiscoverPage() {
  const [events, setEvents] = useState<EventCard[]>([]);
  const [filters, setFilters] = useState({ city: "", category: "", date_filter: "" });
  const [error, setError] = useState("");
  const load = async () => { try { const { data } = await api.get<{ items: EventCard[] }>("/events", { params: { ...filters, city: filters.city || undefined, category: filters.category || undefined, date_filter: filters.date_filter || undefined } }); setEvents(data.items); setError(""); } catch (value) { setError(errorMessage(value)); } };
  useEffect(() => { void load(); }, []);
  return <><section className="mb-12 grid items-end gap-8 lg:grid-cols-[1fr_auto]"><div><p className="mb-4 text-sm font-bold uppercase tracking-[.35em] text-mint">Upcoming experiences</p><h1 className="max-w-4xl font-display text-6xl leading-[1.05] md:text-8xl">Find your seat.<br /><span className="text-white/30">Keep it yours.</span></h1></div><p className="max-w-sm text-white/55">Live availability is derived from confirmed bookings and active holds—never a stale boolean.</p></section>
    <div className="mb-8 grid gap-3 rounded-2xl border border-white/10 bg-panel p-4 md:grid-cols-4"><input className="input" placeholder="City" value={filters.city} onChange={(e) => setFilters({ ...filters, city: e.target.value })} /><input className="input" placeholder="Category" value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })} /><input className="input" type="date" value={filters.date_filter} onChange={(e) => setFilters({ ...filters, date_filter: e.target.value })} /><button onClick={() => void load()} className="rounded-xl bg-mint font-bold text-ink">Apply filters</button></div>
    {error && <Notice message={error} tone="error" />}
    <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">{events.map((event, index) => <Link key={event.id} to={`/events/${event.id}`} className="group rounded-2xl border border-white/10 bg-panel p-6 transition hover:-translate-y-1 hover:border-mint/50"><div className="mb-14 flex items-start justify-between"><span className="rounded-full bg-white/5 px-3 py-1 text-xs font-bold uppercase tracking-wider text-mint">{event.category}</span><span className="text-5xl font-display text-white/10">0{index + 1}</span></div><h2 className="font-display text-3xl">{event.title}</h2><p className="mt-3 line-clamp-2 text-sm text-white/50">{event.description}</p><div className="mt-6 flex items-center justify-between text-sm"><span className="flex items-center gap-2 text-white/60"><MapPin size={15} /> {new Date(event.next_show).toLocaleString()}</span><ArrowRight className="text-mint transition group-hover:translate-x-1" /></div></Link>)}</div>
    {!error && events.length === 0 && <div className="rounded-2xl border border-dashed border-white/15 p-16 text-center text-white/45">No upcoming events match these filters.</div>}</>;
}
