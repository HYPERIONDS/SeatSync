import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Notice } from "../components/Notice";
import { useAuth } from "../hooks/useAuth";
import type { Role } from "../types";
import { errorMessage } from "../utils";

export function AuthPage() {
  const [registering, setRegistering] = useState(false);
  const [form, setForm] = useState({ fullName: "", email: "", password: "", role: "CUSTOMER" as Role });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const auth = useAuth();
  const navigate = useNavigate();
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const signedInUser = registering
        ? await auth.register(form.fullName, form.email, form.password, form.role)
        : await auth.login(form.email, form.password);
      navigate(["ORGANIZER", "ADMIN"].includes(signedInUser.role) ? "/organizer" : "/");
    } catch (value) { setError(errorMessage(value)); } finally { setBusy(false); }
  };
  return <div className="mx-auto grid max-w-4xl overflow-hidden rounded-3xl border border-white/10 bg-panel md:grid-cols-2">
    <section className="bg-gradient-to-br from-mint/25 to-transparent p-10"><p className="mb-3 text-sm font-semibold uppercase tracking-[.3em] text-mint">Race-condition proof</p><h1 className="font-display text-5xl leading-tight">One seat.<br />One winner.</h1><p className="mt-6 text-white/60">Five-minute Redis holds meet durable PostgreSQL guarantees.</p></section>
    <form onSubmit={submit} className="space-y-5 p-10"><h2 className="text-2xl font-semibold">{registering ? "Create an account" : "Welcome back"}</h2>{error && <Notice message={error} tone="error" />}
      {registering && <input required placeholder="Full name" className="input" value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} />}
      <input required type="email" placeholder="Email" className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <input required minLength={10} type="password" placeholder="Password (10+ characters)" className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
      {registering && <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}><option value="CUSTOMER">Customer</option><option value="ORGANIZER">Organizer</option></select>}
      <button disabled={busy} className="w-full rounded-xl bg-mint py-3 font-bold text-ink disabled:opacity-50">{busy ? "Working…" : registering ? "Register" : "Sign in"}</button>
      <button type="button" onClick={() => setRegistering(!registering)} className="w-full text-sm text-white/55 hover:text-mint">{registering ? "Already registered? Sign in" : "New here? Create an account"}</button>
    </form>
  </div>;
}
