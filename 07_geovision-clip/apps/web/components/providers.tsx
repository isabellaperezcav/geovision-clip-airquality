"use client";

import { ThemeProvider } from "next-themes";
import { TooltipProvider } from "@radix-ui/react-tooltip";
import { Toaster } from "sonner";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem
      disableTransitionOnChange
    >
      <TooltipProvider delayDuration={120} skipDelayDuration={300}>
        {children}
        <Toaster
          position="bottom-right"
          theme="system"
          richColors={false}
          closeButton
          toastOptions={{
            classNames: {
              toast:
                "!bg-[var(--surface-1)] !border !border-[var(--border-subtle)] !text-[var(--foreground)] !rounded-md !shadow-[var(--shadow-elevation-2)]",
              title: "!font-sans !text-sm",
              description: "!font-sans !text-xs !text-[var(--muted-foreground)]",
            },
          }}
        />
      </TooltipProvider>
    </ThemeProvider>
  );
}
