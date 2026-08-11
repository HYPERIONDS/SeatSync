export function money(minor: number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(minor / 100);
}

type ValidationIssue = {
  msg?: unknown;
};

function detailMessage(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return undefined;

  const messages = detail
    .map((issue: ValidationIssue) => typeof issue?.msg === "string" ? issue.msg : undefined)
    .filter((message): message is string => Boolean(message));
  return messages.length ? messages.join(" ") : undefined;
}

export function errorMessage(error: unknown): string {
  if (typeof error === "object" && error && "response" in error) {
    const value = error as { response?: { data?: { detail?: unknown } } };
    return detailMessage(value.response?.data?.detail) ?? "The request could not be completed.";
  }
  return error instanceof Error ? error.message : "The request could not be completed.";
}
