import { FetchOptions, ofetch, FetchError } from "ofetch";
import { getLucaGuideWorkspaceId } from "@/utils/guide/workspace";

export class AuthRedirectError extends Error {
  constructor(message = "Session expired. Redirecting to login.") {
    super(message);
    this.name = "AuthRedirectError";
  }
}

function setAuthorizationHeader(
  options: FetchOptions,
  accessToken: string,
): void {
  if (!(options.headers instanceof Headers)) {
    options.headers = new Headers(options.headers);
  }

  options.headers.set("Authorization", `Bearer ${accessToken}`);
}

export const $fetch = ofetch.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
});

export const $apiAuth = ofetch.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
});

export const $api = ofetch.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",

  async onRequest({ options }: { options: FetchOptions }) {
    const accessToken = await useAuthStore().getAccessToken();

    if (!accessToken) {
      handleSessionExpired("no_valid_token_on_request");
      throw new AuthRedirectError();
    }

    setAuthorizationHeader(options, accessToken);
    options.timeout = options.timeout ?? DEFAULT_API_TIMEOUT;
  },

  async onResponse({ response }) {
    if (response._data?.ok === 0) {
      throw response._data;
    }
  },

  async onResponseError({ response, error }) {
    console.log("API response error:", { response, error });

    const status = (response as any)?.status ?? (error as any)?.statusCode;

    const data = (response as any)?._data;

    if (data) {
      throw (response as any)?._data;
    }

    if (error) {
      throw error;
    }

    const err = new FetchError("Request failed");
    err.status = status;
    err.response = response;
    throw err;
  },
});

// Luca Guide's workspace is scoped per brand: resolve the brand currently
// being browsed from the URL so the right workspace id is sent below.
function getCurrentLucaGuideBrandId(): number | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const match = window.location.pathname.match(/\/brands\/(\d+)(?:\/|$)/);
  const brandId = match ? parseInt(match[1], 10) : NaN;

  return Number.isNaN(brandId) ? undefined : brandId;
}

// TODO: Replace dummy workspace/role headers with real auth once available
export const $lucaGuideApi = ofetch.create({
  baseURL: import.meta.env.VITE_LUCA_GUIDE_API_BASE_URL,

  async onRequest({ options }: { options: FetchOptions }) {
    if (!(options.headers instanceof Headers)) {
      options.headers = new Headers(options.headers);
    }

    const brandId = getCurrentLucaGuideBrandId();
    if (brandId !== undefined) {
      options.headers.set("X-Brand-Id", String(brandId));
    }

    const workspaceId =
      brandId !== undefined ? getLucaGuideWorkspaceId(brandId) : undefined;
    if (workspaceId) {
      options.headers.set("X-Workspace-Id", workspaceId);
    }
    options.headers.set("X-User-Role", "owner");

    // HLG-120: forward the logged-in user's Sinergia JWT so Guide can read this user's Builder
    // context (Builder is per-user). Best-effort — the picker/auto-match degrade gracefully if
    // it's absent, so a missing token must never block a Guide request.
    try {
      const accessToken = await useAuthStore().getAccessToken();
      if (accessToken) {
        options.headers.set("X-Builder-Token", accessToken);
      }
    } catch {
      // no-op: leave the header unset; Builder-backed features simply stay empty
    }

    options.timeout = options.timeout ?? DEFAULT_API_TIMEOUT;
  },

  async onResponseError({ response, error }) {
    const status = (response as any)?.status ?? (error as any)?.statusCode;
    const data = (response as any)?._data;

    if (data) {
      throw data;
    }

    if (error) {
      throw error;
    }

    const err = new FetchError("Request failed");
    err.status = status;
    err.response = response;
    throw err;
  },
});

export function paginationOptionsToQuery({
  range,
  order,
  filter,
}: ApiDefaultPaginationOptions = {}) {
  return {
    range: JSON.stringify(range),
    order: JSON.stringify(order),
    filter: filter?.name ? JSON.stringify(filter) : undefined,
  };
}

export function getDefaultPaginationOptions({
  itemsPerPage,
  search,
}: {
  itemsPerPage: number;
  search: string | undefined;
}): ApiDefaultPaginationOptions {
  return {
    range: [0, itemsPerPage - 1],
    order: { updatedAt: "desc" },
    filter: { name: search },
  };
}

export async function fetchAllItems<T>(
  fetcher: (
    range: [number, number],
  ) => Promise<BaseApiPaginatedResponseData<T>>,
) {
  const pageSize = 20;

  const all: T[] = [];
  let start = 0;
  while (true) {
    const response = await fetcher([start, start + pageSize - 1]);

    const pageItems = response.data;

    // If current fetched page has no items, stop requesting further pages
    if (!pageItems || pageItems.length === 0) break;

    all.push(...pageItems);

    // If the page returned less than pageSize, it was the last page
    if (pageItems.length < pageSize) break;
    start += pageSize;
  }

  return all;
}
