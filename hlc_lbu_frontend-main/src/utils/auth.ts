import { jwtDecode } from "jwt-decode";

let authRedirectInProgress = false;

export function getTokenExpirationMs(token: string): number | undefined {
  try {
    const { exp } = jwtDecode<{ exp: number }>(token);
    return exp * 1000;
  } catch (error) {
    console.error(
      "Token check: Invalid token format or decoding error.",
      error,
    );
    return undefined;
  }
}

export function isTokenValidAndNotExpired(token: string): boolean {
  const expiresAtMs = getTokenExpirationMs(token);
  if (!expiresAtMs) return false;

  return expiresAtMs > Date.now() + API_TOKEN_EXPIRY_BUFFER_SECONDS * 1000;
}

export function getSessionExpiryFireAt(
  refreshToken: string,
  bufferSeconds = SESSION_EXPIRY_BUFFER_SECONDS,
): number | undefined {
  const expiresAtMs = getTokenExpirationMs(refreshToken);
  if (!expiresAtMs) return undefined;

  return expiresAtMs - bufferSeconds * 1000;
}

export function isAuthRedirectInProgress(): boolean {
  return authRedirectInProgress;
}

export function handleSessionExpired(
  cause = "token_expired",
  redirectFullPath?: string,
): void {
  if (authRedirectInProgress) return;
  authRedirectInProgress = true;

  const sessionExpired = cause !== "router_guard_no_token";

  if (sessionExpired) {
    console.warn(
      `Session expired or invalid (${cause}). Redirecting to login.`,
    );
  } else {
    console.warn(`Authentication required (${cause}). Redirecting to login.`);
  }

  const authStore = useAuthStore();
  authStore.logout({
    redirectToLogin: false,
    sessionExpired,
    broadcast: cause !== "router_guard_no_token",
  });

  const fullPath =
    redirectFullPath ??
    window.location.pathname + window.location.search + window.location.hash;

  window.location.assign(
    buildLoginUrlWithRedirect(fullPath, { sessionExpired }),
  );
}
