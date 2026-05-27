import { cn } from "@/lib/utils";

export function GeoVisionLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 28 28"
      role="img"
      aria-label="GeoVisionCLIP"
      className={cn("text-[var(--foreground)]", className)}
    >
      <rect x="0.5" y="0.5" width="27" height="27" rx="6" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />
      <path
        d="M7 18 L14 9 L21 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 22 L14 14 L19 22"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.4"
      />
      <circle cx="14" cy="9" r="1.6" fill="currentColor" />
    </svg>
  );
}
