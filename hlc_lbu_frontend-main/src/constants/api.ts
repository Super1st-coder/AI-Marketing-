export const DEFAULT_API_TIMEOUT = 1000 * 60 * 6; // 6 minutes

export const TOKEN_COOKIE_EXPIRATION_SECONDS = 60 * 60 * 24 * 10; // 10 days

const DEFAULT_API_TOKEN_EXPIRY_BUFFER_SECONDS = 30;
const DEFAULT_SESSION_EXPIRY_BUFFER_SECONDS = 2 * 60;
const DEFAULT_SESSION_EXPIRY_WARNING_SECONDS = 5 * 60;

export const API_TOKEN_EXPIRY_BUFFER_SECONDS = getTokenExpiryBufferSeconds();
export const SESSION_EXPIRY_BUFFER_SECONDS = getSessionExpiryBufferSeconds();
export const SESSION_EXPIRY_WARNING_SECONDS = getSessionExpiryWarningSeconds();

function parseEnvSeconds(envKey: string, fallback: number): number {
  if (!(envKey in import.meta.env)) {
    return fallback;
  }

  const parsed = Number(import.meta.env[envKey]);

  return !Number.isNaN(parsed) && parsed >= 0 ? parsed : fallback;
}

function getTokenExpiryBufferSeconds(): number {
  return parseEnvSeconds(
    "VITE_TOKEN_EXPIRY_BUFFER_SECONDS",
    DEFAULT_API_TOKEN_EXPIRY_BUFFER_SECONDS,
  );
}

function getSessionExpiryBufferSeconds(): number {
  return parseEnvSeconds(
    "VITE_SESSION_EXPIRY_BUFFER_SECONDS",
    DEFAULT_SESSION_EXPIRY_BUFFER_SECONDS,
  );
}

function getSessionExpiryWarningSeconds(): number {
  return parseEnvSeconds(
    "VITE_SESSION_EXPIRY_WARNING_SECONDS",
    DEFAULT_SESSION_EXPIRY_WARNING_SECONDS,
  );
}
