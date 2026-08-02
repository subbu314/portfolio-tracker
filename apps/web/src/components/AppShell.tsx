"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Overview", icon: "◉" },
  { href: "/holdings", label: "Holdings", icon: "☰" },
  { href: "/import", label: "Import", icon: "↑" },
  { href: "/settings", label: "Settings", icon: "⚙" },
  { href: "/glossary", label: "Glossary", icon: "?" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-shell" data-testid="app-shell" data-collapsed={collapsed ? "true" : "false"}>
      <aside className="app-nav">
        <div className="app-brand">
          <span className="nav-label">Portfolio Tracker</span>
          {collapsed ? <span aria-hidden>PT</span> : null}
        </div>
        <nav aria-label="Primary">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-label={item.label}
              data-active={isActive(pathname, item.href) ? "true" : "false"}
            >
              <span aria-hidden>{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </nav>
        <button
          type="button"
          className="nav-toggle"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          onClick={() => setCollapsed((v) => !v)}
        >
          <span className="nav-label">{collapsed ? "Expand" : "Collapse"}</span>
          <span aria-hidden>{collapsed ? "»" : "«"}</span>
        </button>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}
