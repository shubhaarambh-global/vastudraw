export type NavigationKey =
  | "dashboard"
  | "projects"
  | "new-plan"
  | "analyze-plan"
  | "editor"
  | "reviews"
  | "exports"
  | "pricing"
  | "billing"
  | "settings";

export type NavigationGroup = "workspace" | "create" | "design" | "account";

export interface NavigationItem {
  readonly key: NavigationKey;
  readonly label: string;
  readonly href: string;
  readonly group: NavigationGroup;
  readonly icon:
    | "dashboard"
    | "projects"
    | "new-plan"
    | "analyze-plan"
    | "editor"
    | "reviews"
    | "exports"
    | "pricing"
    | "billing"
    | "settings";
}

export const navigationItems: readonly NavigationItem[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    href: "/dashboard",
    group: "workspace",
    icon: "dashboard",
  },
  {
    key: "projects",
    label: "Projects",
    href: "/projects",
    group: "workspace",
    icon: "projects",
  },
  {
    key: "new-plan",
    label: "New plan",
    href: "/generation?mode=new",
    group: "create",
    icon: "new-plan",
  },
  {
    key: "analyze-plan",
    label: "Analyze plan",
    href: "/generation?mode=existing",
    group: "create",
    icon: "analyze-plan",
  },
  {
    key: "editor",
    label: "Editor",
    href: "/editor",
    group: "design",
    icon: "editor",
  },
  {
    key: "reviews",
    label: "Vastu review",
    href: "/reviews",
    group: "design",
    icon: "reviews",
  },
  {
    key: "exports",
    label: "Exports",
    href: "/exports",
    group: "design",
    icon: "exports",
  },
  {
    key: "pricing",
    label: "Pricing",
    href: "/pricing",
    group: "account",
    icon: "pricing",
  },
  {
    key: "billing",
    label: "Billing & usage",
    href: "/billing",
    group: "account",
    icon: "billing",
  },
  {
    key: "settings",
    label: "Settings",
    href: "/settings",
    group: "account",
    icon: "settings",
  },
] as const;

export const navigationGroups: readonly {
  readonly key: NavigationGroup;
  readonly label: string;
}[] = [
  { key: "workspace", label: "Workspace" },
  { key: "create", label: "Create" },
  { key: "design", label: "Design" },
  { key: "account", label: "Account" },
] as const;

export function activeNavigationKey(
  pathname: string,
  generationMode?: string | null,
): NavigationKey {
  if (pathname.startsWith("/dashboard")) {
    return "dashboard";
  }

  if (pathname.startsWith("/projects")) {
    return "projects";
  }

  if (pathname.startsWith("/generation")) {
    return generationMode === "existing" ? "analyze-plan" : "new-plan";
  }

  if (pathname.startsWith("/editor")) {
    return "editor";
  }

  if (pathname.startsWith("/reviews")) {
    return "reviews";
  }

  if (pathname.startsWith("/exports")) {
    return "exports";
  }

  if (pathname.startsWith("/pricing")) {
    return "pricing";
  }

  if (pathname.startsWith("/billing")) {
    return "billing";
  }

  if (pathname.startsWith("/settings")) {
    return "settings";
  }

  return "dashboard";
}
