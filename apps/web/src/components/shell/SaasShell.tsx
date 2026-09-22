"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import {
  activeNavigationKey,
  navigationGroups,
  navigationItems,
  type NavigationItem,
} from "./navigation.ts";
import { VastudrawBrandMark } from "./VastudrawBrandMark.tsx";

interface SaasShellProps {
  readonly children: ReactNode;
  readonly userLabel: string;
  readonly environmentLabel?: string;
  readonly contentClassName?: string;
}

function NavGlyph({ item }: { readonly item: NavigationItem }) {
  const common = {
    width: 18,
    height: 18,
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
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      );

    case "projects":
      return (
        <svg {...common}>
          <path d="M3.5 6.5h6l1.8 2H20.5v10.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2Z" />
          <path d="M3.5 8.5h17" />
        </svg>
      );

    case "new-plan":
      return (
        <svg {...common}>
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <path d="M12 8v8M8 12h8" />
        </svg>
      );

    case "analyze-plan":
      return (
        <svg {...common}>
          <path d="M4 19V5a2 2 0 0 1 2-2h8l6 6v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z" />
          <path d="M14 3v6h6" />
          <circle cx="10" cy="14" r="2.5" />
          <path d="m12 16 2 2" />
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

    case "pricing":
      return (
        <svg {...common}>
          <path d="M20 12 12 20l-8-8V4h8Z" />
          <circle cx="9" cy="9" r="1" />
        </svg>
      );

    case "billing":
      return (
        <svg {...common}>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="M3 9h18" />
          <path d="M7 15h4" />
        </svg>
      );

    case "settings":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1" />
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
    return "VD";
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
  const [generationMode, setGenerationMode] = useState<string | null>(null);

  useEffect(() => {
    if (!pathname.startsWith("/generation")) {
      setGenerationMode(null);
      return;
    }

    const params = new URLSearchParams(window.location.search);
    setGenerationMode(params.get("mode"));
  }, [pathname]);

  const activeKey = activeNavigationKey(pathname, generationMode);

  return (
    <div className="saas-shell">
      <aside className="saas-sidebar">
        <Link
          className="saas-brand"
          href="/dashboard"
          aria-label="Vastudraw dashboard"
        >
          <VastudrawBrandMark size={42} className="vastudraw-sidebar-mark" />

          <span>
            <strong>Vastudraw</strong>
            <small>AI architectural planning</small>
          </span>
        </Link>

        <nav
          className="saas-nav saas-nav-grouped"
          aria-label="Primary navigation"
        >
          {navigationGroups.map((group) => (
            <section className="saas-nav-section" key={group.key}>
              <p className="saas-nav-section-label">{group.label}</p>

              <div className="saas-nav-section-items">
                {navigationItems
                  .filter((item) => item.group === group.key)
                  .map((item) => {
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
              </div>
            </section>
          ))}
        </nav>

        <div className="saas-sidebar-spacer" />

        <section className="saas-release-card" aria-label="Vastu rules status">
          <div className="saas-release-card-main">
            <span className="saas-release-icon">V1</span>

            <div>
              <strong>Vastu rules v1</strong>
              <span>4 reviewed rules ? frozen</span>
            </div>

            <span className="saas-ready-dot" aria-label="Ready" />
          </div>

          <Link className="saas-release-pricing-link" href="/pricing">
            View plans
            <span aria-hidden="true">?</span>
          </Link>
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
