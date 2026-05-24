import { cn } from "@/lib/utils";

export function StationMarker({
  className,
  active = false,
}: {
  className?: string;
  active?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={cn(
        "drop-shadow-[0_1px_2px_rgba(0,0,0,0.3)]",
        active ? "text-[var(--info)]" : "text-[var(--foreground)]",
        className,
      )}
      aria-hidden
    >
      <circle cx="8" cy="8" r="6" fill="var(--background)" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="8" cy="8" r="2.5" fill="currentColor" />
      {active && (
        <circle
          cx="8"
          cy="8"
          r="7.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.4"
        />
      )}
    </svg>
  );
}
