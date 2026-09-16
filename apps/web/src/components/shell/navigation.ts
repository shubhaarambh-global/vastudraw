export type NavigationKey =
  | "dashboard"
  | "projects"
  | "editor"
  | "generation"
  | "reviews"
  | "exports"
  | "settings";

export interface NavigationItem {
  readonly key: NavigationKey;
  readonly label: string;
  readonly href: string;
  readonly icon:
    | "dashboard"
    | "projects"
    | "editor"
    | "generation"
    | "reviews"
    | "exports"
    | "settings";
}

export const navigationItems: readonly NavigationItem[] = [
  { key: "dashboard", label: "Dashboard", href: "/", icon: "dashboard" },
  { key: "projects", label: "Projects", href: "/projects", icon: "projects" },
  { key: "editor", label: "Editor", href: "/editor", icon: "editor" },
  {
    key: "generation",
    label: "Generation",
    href: "/generation",
    icon: "generation",
  },
  { key: "reviews", label: "Reviews", href: "/reviews", icon: "reviews" },
  { key: "exports", label: "Exports", href: "/exports", icon: "exports" },
  { key: "settings", label: "Settings", href: "/settings", icon: "settings" },
] as const;

export function activeNavigationKey(pathname: string): NavigationKey {
  if (pathname === "/") {
    return "dashboard";
  }
  if (pathname.startsWith("/projects")) {
    return "projects";
  }
  if (pathname.startsWith("/editor")) {
    return "editor";
  }
  if (pathname.startsWith("/generation")) {
    return "generation";
  }
  if (pathname.startsWith("/reviews")) {
    return "reviews";
  }
  if (pathname.startsWith("/exports")) {
    return "exports";
  }
  if (pathname.startsWith("/settings")) {
    return "settings";
  }
  return "dashboard";
}
