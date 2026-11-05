import type {
  LocationQueryValue,
  RouteLocationRaw,
  RouteLocationResolved,
  Router,
} from "vue-router";
import { appLocales } from "@/plugins/i18n";
import { isGuestRouteName } from "@/router/guest-routes";

const APP_LOCALE_CODES = new Set(Object.keys(appLocales));

function pathWithoutQueryAndHash(fullPath: string): string {
  return fullPath.split("?")[0]?.split("#")[0] ?? "";
}

/** Locale prefix from a URL path (`/es/brands` → `es`). */
function extractLocaleFromPath(fullPath: string): string | undefined {
  const firstSegment = pathWithoutQueryAndHash(fullPath)
    .split("/")
    .filter(Boolean)[0];

  if (firstSegment && APP_LOCALE_CODES.has(firstSegment)) {
    return firstSegment;
  }

  return undefined;
}

function buildLoginBasePath(locale: string | undefined): string {
  return locale ? `/${locale}` : "/";
}

function getRedirectParam(
  redirect: LocationQueryValue | LocationQueryValue[] | undefined,
): string | undefined {
  const value = Array.isArray(redirect) ? redirect[0] : redirect;
  if (!value || typeof value !== "string") return undefined;

  return value;
}

function isExternalOrUnsafePath(path: string): boolean {
  if (!path.startsWith("/") || path.startsWith("//")) return true;
  return /^\s*https?:\/\//i.test(path);
}

/** Whether the path should be stored when forcing the user back to login. */
export function isRedirectablePath(fullPath: string): boolean {
  if (!fullPath || isExternalOrUnsafePath(fullPath)) return false;

  const pathOnly = pathWithoutQueryAndHash(fullPath);

  if (pathOnly === "/" || pathOnly === "") return false;
  if (APP_LOCALE_CODES.has(pathOnly.slice(1))) return false;

  const segments = pathOnly.split("/").filter(Boolean);
  const routeSegment = APP_LOCALE_CODES.has(segments[0] ?? "")
    ? segments[1]
    : segments[0];

  if (!routeSegment) {
    return false;
  }

  return true;
}

export function isSessionExpiredQuery(
  value: LocationQueryValue | LocationQueryValue[] | undefined,
): boolean {
  const sessionExpired = Array.isArray(value) ? value[0] : value;
  return sessionExpired === "1" || sessionExpired === "true";
}

export function buildLoginUrlWithRedirect(
  fullPath: string | undefined,
  {
    sessionExpired = false,
  }: {
    sessionExpired?: boolean;
  } = {},
): string {
  const locale = fullPath ? extractLocaleFromPath(fullPath) : undefined;
  const loginBase = buildLoginBasePath(locale);

  const params = new URLSearchParams();
  if (fullPath && isRedirectablePath(fullPath)) {
    params.set(AUTH_REDIRECT_QUERY_KEY, fullPath);
  }

  if (sessionExpired) {
    params.set(AUTH_SESSION_EXPIRED_QUERY_KEY, "1");
  }

  const query = params.toString();
  return query ? `${loginBase}?${query}` : loginBase;
}

/**
 * Resolves a post-login destination from the login query param.
 * Returns null when the path is missing, external, or not a known app route.
 */
export function resolvePostLoginRedirect(
  router: Router,
  redirect: LocationQueryValue | LocationQueryValue[] | undefined,
): RouteLocationRaw | null {
  const path = getRedirectParam(redirect);
  if (!path || !isRedirectablePath(path) || isExternalOrUnsafePath(path)) {
    return null;
  }

  let resolved: RouteLocationResolved | null;
  try {
    resolved = router.resolve(path);
  } catch (e: unknown) {
    console.error(e);
    return null;
  }

  const name = resolved.name;
  if (typeof name !== "string" || isGuestRouteName(name)) {
    return null;
  }

  if (resolved.matched.length === 0) {
    return null;
  }

  const leaf = resolved.matched[resolved.matched.length - 1];
  if (!leaf?.name) {
    return null;
  }

  const hasAuthenticatedRoute = resolved.matched.some(
    (record) => record.meta.requiresAuth === true,
  );
  if (!hasAuthenticatedRoute) {
    return null;
  }

  return {
    name,
    params: resolved.params,
    query: resolved.query,
    hash: resolved.hash,
  };
}
