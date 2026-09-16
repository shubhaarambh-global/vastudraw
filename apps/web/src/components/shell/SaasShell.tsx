"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import {
  activeNavigationKey,
  navigationItems,
  type NavigationItem,
} from "./navigation.ts";

interface SaasShellProps {
  readonly children: ReactNode;
  readonly userLabel: string;
  readonly environmentLabel?: string;
  readonly contentClassName?: string;
}

function NavGlyph({ item }: { readonly item: NavigationItem }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (item.icon) {
    case "dashboard":
      return (
        <svg {...common}>
          <path d="M3 10.5 12 3l9 7.5" />
          <path d="M5.5 9.5V21h13V9.5" />
          <path d="M9.5 21v-6h5v6" />
        </svg>
      );
    case "projects":
      return (
        <svg {...common}>
          <path d="M3.5 6.5h6l1.8 2H20.5v10.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2Z" />
          <path d="M3.5 8.5h17" />
        </svg>
      );
    case "editor":
      return (
        <svg {...common}>
          <path d="M4 20h4l11-11-4-4L4 16Z" />
          <path d="m13.5 6.5 4 4" />
          <path d="M4 4h6" />
        </svg>
      );
    case "generation":
      return (
        <svg {...common}>
          <path d="m13 2-7 12h6l-1 8 7-12h-6Z" />
        </svg>
      );
    case "reviews":
      return (
        <svg {...common}>
          <path d="M12 3 4.5 6v5.8c0 4.5 3 7.6 7.5 9.2 4.5-1.6 7.5-4.7 7.5-9.2V6Z" />
          <path d="m8.5 12 2.2 2.2 4.8-5" />
        </svg>
      );
    case "exports":
      return (
        <svg {...common}>
          <path d="M12 3v12" />
          <path d="m8 7 4-4 4 4" />
          <path d="M5 13v7h14v-7" />
        </svg>
      );
    case "settings":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.8 1.8 0 0 0 .4 2l.1.1-2.8 2.8-.1-.1a1.8 1.8 0 0 0-2-.4 1.8 1.8 0 0 0-1.1 1.6V21h-4v-.1A1.8 1.8 0 0 0 8.8 19a1.8 1.8 0 0 0-2 .4l-.1.1-2.8-2.8.1-.1a1.8 1.8 0 0 0 .4-2A1.8 1.8 0 0 0 2.9 13H3v-4h-.1A1.8 1.8 0 0 0 4.4 8a1.8 1.8 0 0 0-.4-2l-.1-.1 2.8-2.8.1.1a1.8 1.8 0 0 0 2 .4A1.8 1.8 0 0 0 9.9 2H10v4h4V2h.1a1.8 1.8 0 0 0 1.1 1.6 1.8 1.8 0 0 0 2-.4l.1-.1 2.8 2.8-.1.1a1.8 1.8 0 0 0-.4 2A1.8 1.8 0 0 0 21.1 9H21v4h.1a1.8 1.8 0 0 0-1.7 2Z" />
        </svg>
      );
  }
}

function initials(label: string): string {
  const words = label
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 0);
  if (words.length === 0) {
    return "AI";
  }
  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

export function SaasShell({
  children,
  userLabel,
  environmentLabel = "Development Workspace",
  contentClassName,
}: SaasShellProps) {
  const pathname = usePathname();
  const activeKey = activeNavigationKey(pathname);

  return (
    <div className="saas-shell">
      <aside className="saas-sidebar">
        <Link
          className="saas-brand"
          href="/"
          aria-label="AI Vastu Architect dashboard"
        >
          <span className="saas-brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M5 14.5 16 5l11 9.5V27H5Z" />
              <path d="M11 27V16h10v11" />
              <path d="M16 9c5 2 6 6 3 10-4 0-7-2-7-5 0-2 1-4 4-5Z" />
            </svg>
          </span>
          <span>
            <strong>AI Vastu Architect</strong>
            <small>Deterministic space planning</small>
          </span>
        </Link>

        <nav className="saas-nav" aria-label="Primary navigation">
          {navigationItems.map((item) => {
            const active = activeKey === item.key;
            return (
              <Link
                key={item.key}
                href={item.href}
                className="saas-nav-item"
                data-active={active}
                aria-current={active ? "page" : undefined}
              >
                <NavGlyph item={item} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="saas-sidebar-spacer" />

        <section
          className="saas-release-card"
          aria-label="Production Vastu bundle status"
        >
          <span className="saas-release-icon">V1</span>
          <div>
            <strong>Production Vastu v1</strong>
            <span>4 reviewed rules · frozen</span>
          </div>
          <span className="saas-ready-dot" aria-label="Ready" />
        </section>
      </aside>

      <div className="saas-stage">
        <header className="saas-topbar">
          <div className="saas-workspace-chip">
            <span className="saas-workspace-dot" />
            <span>{environmentLabel}</span>
          </div>
          <div className="saas-topbar-spacer" />
          <div className="saas-user">
            <span className="saas-avatar">{initials(userLabel)}</span>
            <span className="saas-user-copy">
              <strong>{userLabel}</strong>
              <small>Workspace member</small>
            </span>
          </div>
        </header>

        <div
          className={
            contentClassName
              ? `saas-content ${contentClassName}`
              : "saas-content"
          }
        >
          {children}
        </div>
      </div>
    </div>
  );
}
