export type SaveLockingResult = undefined | "confirm" | "cancel";
export type SaveLockingCallback = () => Promise<SaveLockingResult>;

/**
 * Store to manage save locking mechanism to prevent navigating or actions while a form is not saved.
 * Uses an array of Symbols to track individual locks.
 */
export const useSaveLockingStore = defineStore("SaveLockingStore", () => {
  const locks = ref<symbol[]>([]);
  const callbacks = ref<SaveLockingCallback[]>([]);

  const isLocked = computed(() => locks.value.length > 0);

  function clearBeforeUnloadListener() {
    window.removeEventListener("beforeunload", handleBeforeUnload);
  }

  function handleBeforeUnload(event: BeforeUnloadEvent) {
    if (isAuthRedirectInProgress()) return;

    event.preventDefault();
    event.returnValue = "";
  }

  watch(isLocked, (locked) => {
    if (locked) {
      window.addEventListener("beforeunload", handleBeforeUnload);
    } else {
      clearBeforeUnloadListener();
    }
  });

  function lock(modalId: symbol, callback: SaveLockingCallback) {
    if (locks.value.includes(modalId)) return;
    locks.value.push(modalId);
    callbacks.value.push(callback);
  }

  function unlock(modalId: symbol) {
    const index = locks.value.indexOf(modalId);
    if (index !== -1) {
      locks.value.splice(index, 1);
      callbacks.value.splice(index, 1);
    }
  }

  function releaseAllLocks() {
    locks.value = [];
    callbacks.value = [];
    clearBeforeUnloadListener();
  }

  async function execute(
    options: { onlyId?: Symbol } = {},
  ): Promise<SaveLockingResult> {
    if (isAuthRedirectInProgress()) {
      return "confirm";
    }

    if (!isLocked.value) {
      return undefined;
    }

    console.log("Save locking executed");
    const targetLockIndex = locks.value.length - 1;
    const targetLockId = locks.value[targetLockIndex];

    if (options.onlyId && options.onlyId !== targetLockId) return;

    const callback = callbacks.value[targetLockIndex];
    const result = await callback();
    console.log("Save locking result: ", result);
    return result;
  }

  return {
    isLocked,
    lock,
    unlock,
    releaseAllLocks,
    execute,
  };
});
