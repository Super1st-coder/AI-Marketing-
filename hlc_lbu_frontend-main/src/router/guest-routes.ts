import type { RouteRecordName, RouteRecordRaw } from "vue-router";

/**
 * Named routes that are reachable without `meta.requiresAuth` on the record
 * or any of its ancestors (login, register, OAuth callbacks, etc.).
 */
export function collectGuestRouteNames(
  routes: RouteRecordRaw[],
  ancestorRequiresAuth = false,
): Set<string> {
  const names = new Set<string>();

  for (const route of routes) {
    const requiresAuth =
      ancestorRequiresAuth || route.meta?.requiresAuth === true;

    if (typeof route.name === "string" && !requiresAuth) {
      names.add(route.name);
    }

    if (route.children?.length) {
      for (const name of collectGuestRouteNames(route.children, requiresAuth)) {
        names.add(name);
      }
    }
  }

  return names;
}

let guestRouteNames = new Set<string>();

export function registerGuestRouteNames(
  routes: RouteRecordRaw[],
): ReadonlySet<string> {
  guestRouteNames = collectGuestRouteNames(routes);
  return guestRouteNames;
}

export function getGuestRouteNames(): ReadonlySet<string> {
  return guestRouteNames;
}

export function isGuestRouteName(
  name: RouteRecordName | null | undefined,
): boolean {
  return typeof name === "string" && guestRouteNames.has(name);
}
