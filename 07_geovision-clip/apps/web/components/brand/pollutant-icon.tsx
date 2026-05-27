import { cn } from "@/lib/utils";
import type { Pollutant } from "@/lib/domain";

type Props = { pollutant: Pollutant; className?: string };

export function PollutantIcon({ pollutant, className }: Props) {
  const base = "shrink-0";
  if (pollutant === "NO2") {
    return (
      <svg
        viewBox="0 0 24 24"
        className={cn(base, className)}
        role="img"
        aria-label="NO2"
      >
        <circle cx="6" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="13" cy="8" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="13" cy="16" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <line x1="8.8" y1="10.5" x2="11" y2="9" stroke="currentColor" strokeWidth="1.2" />
        <line x1="8.8" y1="13.5" x2="11" y2="15" stroke="currentColor" strokeWidth="1.2" />
        <text x="18" y="11" fontSize="6" fill="currentColor" fontFamily="ui-monospace" fontWeight="600">
          N
        </text>
        <text x="18" y="18" fontSize="5" fill="currentColor" fontFamily="ui-monospace" opacity="0.7">
          O₂
        </text>
      </svg>
    );
  }
  if (pollutant === "SO2") {
    return (
      <svg
        viewBox="0 0 24 24"
        className={cn(base, className)}
        role="img"
        aria-label="SO2"
      >
        <circle cx="6" cy="12" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="13.5" cy="7.5" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="13.5" cy="16.5" r="2.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <line x1="8.9" y1="10.3" x2="11.5" y2="8.6" stroke="currentColor" strokeWidth="1.2" />
        <line x1="8.9" y1="13.7" x2="11.5" y2="15.4" stroke="currentColor" strokeWidth="1.2" />
        <text x="18" y="11" fontSize="6" fill="currentColor" fontFamily="ui-monospace" fontWeight="600">
          S
        </text>
        <text x="18" y="18" fontSize="5" fill="currentColor" fontFamily="ui-monospace" opacity="0.7">
          O₂
        </text>
      </svg>
    );
  }
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn(base, className)}
      role="img"
      aria-label="O3"
    >
      <circle cx="7" cy="12" r="2.8" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="12.5" cy="8" r="2.8" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="12.5" cy="16" r="2.8" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <text x="18" y="14" fontSize="7" fill="currentColor" fontFamily="ui-monospace" fontWeight="600">
        O₃
      </text>
    </svg>
  );
}
