import type { LocationQueryValue } from "vue-router";

/**
 * Reads an email from a route query param.
 *
 * Workaround: the backend builds email links (signup, password reset,
 * unsubscribe) without URL-encoding the email, so a "+" in the address
 * (e.g. "user+1@example.com") is decoded as a space. Emails can't contain
 * spaces, so restoring them as "+" keeps links that were already sent working.
 * Can be removed once the backend encodes the email and old links expire.
 */
export function getEmailFromQuery(
  value: LocationQueryValue | LocationQueryValue[] | undefined,
): string {
  const email = Array.isArray(value) ? value[0] : value;

  return (email ?? "").replace(/ /g, "+");
}

export function isUrlAPdf(src: string) {
  return src.toLowerCase().includes(".pdf");
}

export function getFileExtensionFromUrl(url: string): string | undefined;

export function getFileExtensionFromUrl(url: string, fallback: string): string;

export function getFileExtensionFromUrl(
  url: string,
  fallback: string | undefined,
): string | undefined;

export function getFileExtensionFromUrl(
  url: string,
  fallback: string | undefined = undefined,
): string | undefined {
  try {
    const lastSegment = new URL(url).pathname.split("/").pop() ?? "";
    const match = lastSegment.match(/\.([a-zA-Z0-9]+)$/);
    if (match) return match[1].toLowerCase();
  } catch (e: unknown) {
    console.error(e);
    // invalid URL
  }
  return fallback;
}
