export default function useSaveLock(
  isLocked: MaybeRefOrGetter<boolean>,
  onLocked: SaveLockingCallback,
) {
  const lockId = ref(Symbol("saveLock"));
  const store = useSaveLockingStore();

  const _isLocked = computed(() => toValue(isLocked));

  function lock() {
    store.lock(lockId.value, onLocked);
  }

  function unlock() {
    store.unlock(lockId.value);
  }

  watch(
    _isLocked,
    (value) => {
      if (value) {
        lock();
      } else {
        unlock();
      }
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    unlock();
  });

  // Execute lock on vue router navigation
  onBeforeRouteLeave(async () => {
    if (isAuthRedirectInProgress()) return true;

    const reponse = await store.execute({ onlyId: lockId.value });

    if (reponse === "cancel") {
      return false;
    }
  });

  return {};
}
