"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  List,
  Settings,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/holdings", label: "Holdings", icon: List },
  { href: "/import", label: "Import", icon: Upload },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/glossary", label: "Glossary", icon: BookOpen },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className={cn(
        "grid min-h-screen transition-[grid-template-columns] duration-200",
        collapsed ? "grid-cols-[64px_1fr]" : "grid-cols-[220px_1fr]",
      )}
      data-testid="app-shell"
      data-collapsed={collapsed ? "true" : "false"}
    >
      <aside className="flex flex-col gap-4 border-r border-border bg-surface/95 p-3">
        <div className="px-2 py-1 text-sm font-semibold tracking-wide">
          <span className={cn(collapsed && "sr-only")}>Portfolio Tracker</span>
          {collapsed ? <span aria-hidden>PT</span> : null}
        </div>
        <nav aria-label="Primary" className="flex flex-col gap-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.label}
                data-active={active ? "true" : "false"}
                className={cn(
                  "flex items-center gap-3 rounded-md px-2.5 py-2 text-sm text-muted-foreground transition-colors",
                  active && "bg-surface-elevated text-foreground",
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden />
                <span className={cn(collapsed && "sr-only")}>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-auto"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          onClick={() => setCollapsed((v) => !v)}
        >
          {collapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
          <span className={cn(collapsed && "sr-only")}>
            {collapsed ? "Expand" : "Collapse"}
          </span>
        </Button>
      </aside>
      <main className="mx-auto w-full max-w-[1200px] px-7 py-6 pb-12">{children}</main>
    </div>
  );
}
