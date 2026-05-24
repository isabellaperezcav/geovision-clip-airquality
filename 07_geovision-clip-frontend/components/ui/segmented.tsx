"use client";

import { cn } from "@/lib/utils";

type SegmentedItem<T extends string> = {
  value: T;
  label: string;
  description?: string;
  icon?: React.ReactNode;
};

export interface SegmentedProps<T extends string> {
  items: ReadonlyArray<SegmentedItem<T>>;
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
  size?: "sm" | "md";
  fullWidth?: boolean;
}

export function Segmented<T extends string>({
  items,
  value,
  onChange,
  ariaLabel,
  size = "md",
  fullWidth = false,
}: SegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex rounded-[8px] border border-[var(--border-subtle)] bg-[var(--surface-2)] p-[3px]",
        fullWidth && "w-full",
      )}
    >
      {items.map((item) => {
        const selected = item.value === value;
        return (
          <button
            key={item.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(item.value)}
            title={item.description}
            className={cn(
              "relative inline-flex items-center justify-center gap-1.5 rounded-[6px] font-medium",
              "transition-[background,color,box-shadow] duration-[var(--speed-quick)]",
              size === "md" ? "h-7 px-3 text-[13px]" : "h-6 px-2.5 text-[12px]",
              fullWidth && "flex-1",
              selected
                ? "bg-[var(--background)] text-[var(--foreground)] shadow-[var(--shadow-elevation-1)]"
                : "text-[var(--muted)] hover:text-[var(--foreground)]",
            )}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}
