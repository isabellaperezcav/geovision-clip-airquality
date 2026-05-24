"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type Props = {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  icon?: ReactNode;
};

export function ToggleRow({ label, description, checked, onChange, icon }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        "group flex w-full items-start gap-3 rounded-[8px] border border-transparent px-2.5 py-2 text-left",
        "transition-colors duration-[var(--speed-quick)] hover:bg-[var(--surface-2)]",
        "focus-visible:outline-none focus-visible:border-[var(--border-strong)]",
      )}
    >
      {icon && (
        <div className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center text-[var(--muted)]">
          {icon}
        </div>
      )}
      <div className="flex-1">
        <div className="text-[13px] font-medium text-[var(--foreground)]">{label}</div>
        {description && (
          <div className="text-[11px] text-[var(--muted)]">{description}</div>
        )}
      </div>
      <span
        className={cn(
          "relative mt-0.5 inline-flex h-4 w-7 shrink-0 items-center rounded-full transition-colors",
          checked ? "bg-[var(--foreground)]" : "bg-[var(--border-strong)]",
        )}
      >
        <span
          className={cn(
            "inline-block h-3 w-3 rounded-full bg-[var(--background)] shadow-[var(--shadow-elevation-1)] transition-transform",
            checked ? "translate-x-3.5" : "translate-x-0.5",
          )}
        />
      </span>
    </button>
  );
}
