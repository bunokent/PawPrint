import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton", className)} aria-hidden="true" {...props} />;
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="empty">
      <p className="t-h3" style={{ marginBottom: 8 }}>{title}</p>
      {children}
    </div>
  );
}

export function ErrorBox({ message, children }: { message: string; children?: React.ReactNode }) {
  return (
    <div className="error-box" role="alert">
      <p style={{ fontWeight: 600 }}>{message}</p>
      {children}
    </div>
  );
}
