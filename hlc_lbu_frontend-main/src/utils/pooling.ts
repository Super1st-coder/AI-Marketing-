export type PoolingFunctionOptions = {
  maxAttempts?: number; // default: infinite
  delayMs?: number; // delay to first call
  backoffFactor?: number; // default: 1 (no backoff)
  maxInterval?: number; // default: Infinity (uncapped)
  timeoutMs?: number; // default: undefined (no timeout)
  abortSignal?: AbortSignal; // default: undefined (no abort)
};

/**
 * Polls an async function until a condition is met
 * @param fetchFn - Async function that returns a value to be checked
 * @param stopConditionFn - Function that returns true when polling should stop
 * @param interval - Initial milliseconds between polling attempts
 * @param options - Optional controls for backoff, max attempts, delay, and limits
 * @returns Promise that resolves with the final result when condition is met
 */
export async function pooling<T>(
  fetchFn: () => Promise<T>,
  stopConditionFn: (response: T) => boolean,
  interval: number,
  options?: PoolingFunctionOptions,
): Promise<T> {
  const maxAttempts = options?.maxAttempts ?? Infinity;
  const delayMs = options?.delayMs ?? 0;
  const backoffFactor = options?.backoffFactor ?? 1;
  const maxInterval = options?.maxInterval ?? Infinity;
  const timeoutMs = options?.timeoutMs;

  let attempt = 0;
  let currentInterval = interval;
  const start = Date.now();

  if (delayMs) {
    await sleep(delayMs);
  }

  while (attempt < maxAttempts) {
    if (timeoutMs && Date.now() - start > timeoutMs) {
      throw new Error("Polling timed out");
    }

    try {
      const response = await fetchFn();

      if (stopConditionFn(response)) {
        return response;
      }

      // Wait before the next attempt
      await new Promise((resolve) => setTimeout(resolve, currentInterval));
      attempt++;

      // Increase interval using backoff
      if (backoffFactor !== 1) {
        currentInterval = Math.min(
          maxInterval,
          Math.floor(currentInterval * backoffFactor),
        );
      }
    } catch (error) {
      // Re-throw the error to let the caller handle it
      throw error;
    }
  }

  throw new Error("Max polling attempts reached");
}

/**
 * Polls an async function until the returned value is different to oldValue
 */
export async function poolUntilDifference<T>(
  fetchFn: () => Promise<T>,
  oldValue: T,
  interval: number = 1000,
  options: PoolingFunctionOptions = { maxAttempts: 3, delayMs: 500 },
) {
  const newValue = await pooling(
    fetchFn,
    (value) => value !== oldValue && !!value,
    interval,
    options,
  );

  return newValue;
}

/**
 * Polls an async function until the returned value is different to oldValue and the new value is truthy
 */
export async function poolUntilDifferenceAndTruthy<T>(
  fetchFn: () => Promise<T>,
  oldValue: T,
  interval: number = 1000,
  options: PoolingFunctionOptions = { maxAttempts: 3, delayMs: 500 },
) {
  const newValue = await pooling(
    fetchFn,
    (value) => value !== oldValue && !!value,
    interval,
    options,
  );

  return newValue;
}
