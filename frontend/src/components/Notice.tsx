export function Notice({ message, tone = "info" }: { message: string; tone?: "info" | "error" | "success" }) {
  const styles = { info: "border-mint/30 bg-mint/10 text-mint", error: "border-coral/30 bg-coral/10 text-coral", success: "border-mint/30 bg-mint/10 text-mint" };
  return <div role="status" className={`rounded-xl border px-4 py-3 text-sm ${styles[tone]}`}>{message}</div>;
}
