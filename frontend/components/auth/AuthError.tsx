import { CircleAlert } from "lucide-react";

export function AuthError({ message }: { message?: string }) {
  if (!message) return null;
  return <div className="flex items-start gap-2 rounded-lg border border-red-500/25 bg-red-500/[0.06] px-3 py-2.5 text-sm text-red-700 dark:text-red-300" role="alert"><CircleAlert className="mt-0.5 shrink-0" size={16} />{message}</div>;
}
