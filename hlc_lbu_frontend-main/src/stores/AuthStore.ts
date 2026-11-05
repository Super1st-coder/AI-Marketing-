import { defineStore } from "pinia";
import { RouteLocationNormalizedGeneric } from "vue-router";
import { useCookies } from "@vueuse/integrations/useCookies";
import { NetworkError } from "@/services/common-errors";
import { FetchError } from "ofetch";
import i18n from "@/plugins/i18n";

export type RoutePermissionMeta = {
  name: PermissionFunctionName;
  actions: string[];
};

const AUTH_SYNC_BROADCAST_CHANNEL = "hiluca-auth-sync";

type AuthSyncBroadcastMessage =
  { type: "login" } | { type: "logout"; sessionExpired: boolean };

export const useAuthStore = defineStore("AuthStore", () => {
  const router = useRouter();
  // Use the global i18n instance — this store is created from router guards
  // before any component setup context exists (required for lazy locale loading).
  const t = i18n.global.t;
  const locale = i18n.global.locale;
  const notificationStore = useNotificationStore();

  const cookies = useCookies(["accessToken", "refreshToken"]);

  let refreshPromise: Promise<string | undefined> | undefined;
  const sessionExpiryFireAt = ref<number | undefined>();
  const sessionWarningToastId = ref<number | undefined>();
  const sessionWarningInterval = ref<
    ReturnType<typeof setInterval> | undefined
  >();
  const sessionExpiryTimer = ref<ReturnType<typeof setTimeout> | undefined>();
  const sessionWarningTimer = ref<ReturnType<typeof setTimeout> | undefined>();

  let authSyncBroadcastChannel = ref<BroadcastChannel | undefined>();

  if (authSyncBroadcastChannel.value === undefined) {
    authSyncBroadcastChannel.value = new BroadcastChannel(
      AUTH_SYNC_BROADCAST_CHANNEL,
    );

    authSyncBroadcastChannel.value.addEventListener(
      "message",
      (event: MessageEvent) => {
        const message = event.data as AuthSyncBroadcastMessage | undefined;

        if (!message || typeof message !== "object" || !("type" in message)) {
          return;
        }

        if (message.type === "logout" && message.sessionExpired) {
          const fullPath =
            window.location.pathname +
            window.location.search +
            window.location.hash;

          window.location.assign(
            buildLoginUrlWithRedirect(fullPath, { sessionExpired: true }),
          );
          return;
        }

        window.location.reload();
      },
    );
  }

  function broadcastAuthSyncToOtherTabs(message: AuthSyncBroadcastMessage) {
    authSyncBroadcastChannel.value?.postMessage(message);
  }

  const userEmail = useLocalStorage<string | undefined>("username", undefined);
  const userFullname = useLocalStorage<string | undefined>(
    "full_name",
    undefined,
  );
  const userRolesAndPermissions = useLocalStorage<UserRoleAndActions[]>(
    "permissions",
    [],
  );

  // Merge permissions by function_name. For functions that appear multiple
  // times, combine their actions (deduped by id). The merged view intentionally
  // excludes role fields (`rol_name` and `rol_long_name`) — only function and
  // actions are provided.
  const userPermissions = computed(() => {
    const map = new Map<string, UserPermission>();

    for (const permission of userRolesAndPermissions.value) {
      const key = permission.function_name;
      const existing = map.get(key);

      if (!existing) {
        // Create a new object without role fields
        map.set(key, {
          actions: [...permission.actions],
          function_name: permission.function_name,
          function_long_name: permission.function_long_name,
        });

        continue;
      }

      // Merge actions by id (dedupe)
      const actionMap = new Map<string, { id: string; name: string }>();
      for (const action of existing.actions) {
        actionMap.set(action.id, action);
      }
      for (const a of permission.actions) {
        actionMap.set(a.id, a);
      }
      existing.actions = [...actionMap.values()];
      map.set(key, existing);
    }

    return [...map.values()];
  });

  const userNames = computed(() => {
    if (!userFullname.value) return undefined;

    return userFullname.value.split(" ");
  });

  const userInitials = computed(() => {
    if (!userFullname.value) return undefined;
    return getUserInitials(userFullname.value);
  });

  const userInfo = computed(() => {
    if (
      !userEmail.value ||
      !userFullname.value ||
      !userNames.value ||
      !userInitials.value
    )
      return undefined;

    return {
      userEmail: userEmail.value,
      userFullname: userFullname.value,
      userRolesAndPermissions: userRolesAndPermissions.value,
      userPermissions: userPermissions.value,
      userNames: userNames.value,
      userInitials: userInitials.value,
    };
  });

  async function login(data: { email: string; password: string }) {
    // Request
    const response = await $apiAuth<ApiResponseLogin>("/v1/member/login", {
      method: "POST",
      body: {
        username: data.email,
        password: data.password,
      },
    });

    // Save
    cookies.set("accessToken", response.data.access_token, {
      path: "/",
      maxAge: TOKEN_COOKIE_EXPIRATION_SECONDS,
    });
    cookies.set("refreshToken", response.data.refresh_token, {
      path: "/",
      maxAge: TOKEN_COOKIE_EXPIRATION_SECONDS,
    });

    // Save data to localStorage
    userEmail.value = response.data.extra_info.username;
    userFullname.value = response.data.extra_info.full_name;
    userRolesAndPermissions.value = response.data.extra_info.permissions;

    // Schedule the session watchdog
    scheduleSessionWatchdog(response.data.refresh_token);

    broadcastAuthSyncToOtherTabs({ type: "login" });

    // Determine what to redirect to after login using the redirect query param
    const postLoginTarget = resolvePostLoginRedirect(
      router,
      router.currentRoute.value.query[AUTH_REDIRECT_QUERY_KEY],
    );

    // Redirect
    await router.push(postLoginTarget ?? { name: "BrandList" });
  }

  async function logout({
    redirectToLogin = true,
    sessionExpired = false,
    broadcast = true,
  }: {
    redirectToLogin?: boolean;
    sessionExpired?: boolean;
    broadcast?: boolean;
  } = {}) {
    console.log("Logging out user. Clearing tokens and redirecting to login.");

    // Clear the session watchdog
    clearSessionWatchdog();

    // Release all locks
    useSaveLockingStore().releaseAllLocks();

    // Clear tokens
    cookies.remove("accessToken", { path: "/" });
    cookies.remove("refreshToken", { path: "/" });

    if (broadcast) {
      broadcastAuthSyncToOtherTabs({ type: "logout", sessionExpired });
    }

    // Redirect
    if (redirectToLogin) {
      await router.push({ name: "Login" });
    }
  }

  // Helper to check specific permissions against user permissions
  const hasPermissionFor = (requiredPermissions: RoutePermissionMeta[]) => {
    const permissions = userPermissions.value ?? [];

    // The user must satisfy every required permission entry
    const allowed = requiredPermissions.every(
      (requiredPermission: RoutePermissionMeta) => {
        // Find the user's permission entry for the required function
        const targetUserPermission = permissions.find(
          (p) => p.function_name === requiredPermission.name,
        );

        // If the user doesn't have the function at all, deny access
        if (!targetUserPermission) {
          return false;
        }

        // The user is allowed if the actions array is empty
        if (requiredPermission.actions.length === 0) {
          return true;
        }

        // Allow if user has every one of the required actions
        return requiredPermission.actions.every((a) =>
          targetUserPermission.actions.find((_a) => _a.id === a),
        );
      },
    );

    return allowed;
  };

  function _hasValidRefreshSession(): boolean {
    const refreshToken = cookies.get("refreshToken");
    if (!refreshToken) return false;

    const expiresAtMs = getTokenExpirationMs(refreshToken);
    return expiresAtMs !== undefined && expiresAtMs > Date.now();
  }

  async function hasActiveSession(): Promise<boolean> {
    try {
      return Boolean(await getAccessToken());
    } catch (error) {
      if (error instanceof NetworkError && _hasValidRefreshSession()) {
        return true;
      }

      return false;
    }
  }

  async function hasAccessToRoute(to: RouteLocationNormalizedGeneric) {
    if (await hasActiveSession()) {
      // Extract required permissions from the route meta
      const currentMeta = to.matched[to.matched.length - 1].meta;
      const requiredPermissions = currentMeta.requiredPermissions;

      // If there are no permission requirements, allow access
      if (
        requiredPermissions === undefined ||
        requiredPermissions.length === 0
      ) {
        return true;
      }

      // Check permissions
      const allowed = hasPermissionFor(requiredPermissions);
      return allowed;
    }

    return false;
  }

  function _isRefreshAuthFailure(error: unknown): boolean {
    if (!(error instanceof FetchError)) return false;

    const status = error.status ?? error.statusCode;
    return status === 401;
  }

  async function _fetchRefreshedAccessToken(
    refreshToken: string,
  ): Promise<string | undefined> {
    try {
      const response = await $apiAuth<ApiResponseLogin>(
        "/v1/member/token/refresh",
        {
          method: "POST",
          headers: { Authorization: `Bearer ${refreshToken}` },
          timeout: DEFAULT_API_TIMEOUT,
        },
      );

      const newAccessToken = response.data.access_token;
      if (!newAccessToken) {
        console.error("Refresh response did not contain access_token.");
        return undefined;
      }

      cookies.set("accessToken", newAccessToken, {
        path: "/",
        maxAge: TOKEN_COOKIE_EXPIRATION_SECONDS,
      });

      const newPermissions = response.data.extra_info?.permissions;
      if (newPermissions) {
        userRolesAndPermissions.value = newPermissions;
      }

      if (import.meta.env.DEV) {
        console.info("Token refreshed successfully.");
      }

      return newAccessToken;
    } catch (error) {
      console.error(error);

      if (_isRefreshAuthFailure(error)) {
        console.warn("Refresh token rejected by server:", error);
        return undefined;
      }

      console.error("Transient refresh failure:", error);
      throw new NetworkError();
    }
  }

  async function _refreshAccessToken(): Promise<string | undefined> {
    const refreshToken = cookies.get("refreshToken");
    if (!refreshToken) {
      return undefined;
    }

    if (!refreshPromise) {
      refreshPromise = _fetchRefreshedAccessToken(refreshToken).finally(() => {
        refreshPromise = undefined;
      });
    }

    return await refreshPromise;
  }

  async function getAccessToken(): Promise<string | undefined> {
    const existing = cookies.get("accessToken");

    if (existing && isTokenValidAndNotExpired(existing)) {
      return existing;
    }

    return await _refreshAccessToken();
  }

  function getSessionWarningDescription(): string {
    if (sessionExpiryFireAt.value === undefined) return "";

    const remainingMs = sessionExpiryFireAt.value - Date.now();

    return t("auth.session-expiry-warning.description", {
      duration: formatRemainingDuration(locale.value, remainingMs),
    });
  }

  function clearSessionWarningToast() {
    // Clear the interval that updates the toast description continuously
    if (sessionWarningInterval.value !== undefined) {
      clearInterval(sessionWarningInterval.value);
      sessionWarningInterval.value = undefined;
    }

    // Dismiss the toast itself
    if (sessionWarningToastId.value !== undefined) {
      notificationStore.dismiss(sessionWarningToastId.value);
      sessionWarningToastId.value = undefined;
    }
  }

  function clearSessionWatchdog() {
    sessionExpiryFireAt.value = undefined;

    // Clear the session expiry timer
    if (sessionExpiryTimer.value !== undefined) {
      clearTimeout(sessionExpiryTimer.value);
      sessionExpiryTimer.value = undefined;
    }

    // Clear the session toast warning timer
    if (sessionWarningTimer.value !== undefined) {
      clearTimeout(sessionWarningTimer.value);
      sessionWarningTimer.value = undefined;
    }

    // Clear the session warning toast related resources
    clearSessionWarningToast();
  }

  function showSessionExpiryWarning() {
    // Show the session expiry warning toast
    sessionWarningToastId.value = notificationStore.display({
      type: "warning",
      title: t("auth.session-expiry-warning.title"),
      description: getSessionWarningDescription(),
      durationMs: null,
    });

    // Schedule a interval to update the toast description continuously
    sessionWarningInterval.value = setInterval(() => {
      if (
        sessionWarningToastId.value === undefined ||
        sessionExpiryFireAt.value === undefined
      ) {
        return;
      }

      // Update the toast description
      const updated = notificationStore.update(sessionWarningToastId.value, {
        description: getSessionWarningDescription(),
      });

      // If the toast is not updated, it means the toast has been dismissed
      // so we need to clear the session warning toast related resources
      if (!updated) {
        clearSessionWarningToast();
        return;
      }
    }, 1000);
  }

  function scheduleSessionWatchdog(refreshToken: string) {
    // Clear any existing timers to avoid multiple timers running simultaneously
    clearSessionWatchdog();

    // Determine when the session will expire
    const fireAt = getSessionExpiryFireAt(refreshToken);
    if (!fireAt) return;
    sessionExpiryFireAt.value = fireAt;

    // If the session will expire in less than 0 seconds, expire the session immediately
    const delayMs = fireAt - Date.now();
    if (delayMs <= 0) {
      handleSessionExpired("refresh_token_already_expired");
      return;
    }

    // Determine when the session expiry warning will be shown
    const warningAt = fireAt - SESSION_EXPIRY_WARNING_SECONDS * 1000;
    const warningDelayMs = warningAt - Date.now();

    // Schedule the session expiry toast warning
    sessionWarningTimer.value = setTimeout(
      showSessionExpiryWarning,
      warningDelayMs,
    );

    // Schedule the session expiry
    sessionExpiryTimer.value = setTimeout(() => {
      handleSessionExpired("refresh_token_expiring");
    }, delayMs);
  }

  function initSessionWatchdog() {
    const refreshToken = cookies.get("refreshToken");
    if (refreshToken) {
      scheduleSessionWatchdog(refreshToken);
    }
  }

  return {
    getAccessToken,
    hasActiveSession,
    initSessionWatchdog,
    userEmail,
    userFullname,
    userPermissions,
    userRolesAndPermissions,
    userNames,
    userInitials,
    userInfo,
    logout,
    login,
    hasPermissionFor,
    hasAccessToRoute,
  };
});
