"use client";

import { GeoVisionLogo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Search, Code } from "lucide-react";

export function Header({ onOpenCommand }: { onOpenCommand: () => void }) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-[var(--border-subtle)] bg-[var(--background)] px-4">
      <GeoVisionLogo className="h-5 w-5" />
      <div className="flex items-baseline gap-2">
        <span className="text-[13px] font-semibold tracking-tight text-[var(--foreground)]">
          GeoVisionCLIP
        </span>
        <Separator orientation="vertical" className="h-3" />
        <span className="font-mono text-[11px] text-[var(--muted)]">cali · mvp 0.1</span>
      </div>

      <div className="flex-1" />

      <Button
        variant="subtle"
        size="sm"
        onClick={onOpenCommand}
        className="font-mono"
      >
        <Search size={12} strokeWidth={1.8} className="mr-2 text-[var(--muted)]" />
        Buscar
        <kbd className="ml-3 hidden rounded-[4px] border border-[var(--border-subtle)] bg-[var(--background)] px-1.5 py-0.5 text-[10px] text-[var(--muted)] sm:inline-block">
          Ctrl+K
        </kbd>
      </Button>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            asChild
            aria-label="Repositorio del proyecto"
          >
            <a
              href="https://github.com/isabellaperezcav/geovision-clip-airquality"
              target="_blank"
              rel="noreferrer"
              tabIndex={0}
            >
              <Code size={14} strokeWidth={1.6} />
            </a>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom">Repositorio</TooltipContent>
      </Tooltip>

      <ThemeToggle />
    </header>
  );
}
