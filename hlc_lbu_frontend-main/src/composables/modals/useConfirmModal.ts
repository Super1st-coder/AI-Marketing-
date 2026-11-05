export type ConfirmModalInjectionData<T> = {
  isModalOpen: Ref<boolean>;
  handleClose: () => void;
  handleCancel: () => void;
  handleContinue: () => void;
  handleValue: (value: T) => void;
  dontShowAgain: Ref<boolean>;
};

export type ConfirmModalDefaultValues = "close" | "cancel" | "continue";

export default function useConfirmModal<T = ConfirmModalDefaultValues>(
  name = "confirm",
) {
  const isConfirmOpen = ref(false);
  const dontShowAgain = useLocalStorage<boolean>(
    `dontShowAgain.${name}`,
    false,
  );
  const modalContinuePromise =
    ref<(value: T | ConfirmModalDefaultValues) => void>();

  const handleConfirmClose = () => {
    modalContinuePromise.value?.("close");
    isConfirmOpen.value = false;
  };

  const handleConfirmCancel = () => {
    modalContinuePromise.value?.("cancel");
    isConfirmOpen.value = false;
  };

  const handleConfirmContinue = () => {
    modalContinuePromise.value?.("continue");
    isConfirmOpen.value = false;
  };

  const handleValue = (value: T | ConfirmModalDefaultValues) => {
    modalContinuePromise.value?.(value);
    isConfirmOpen.value = false;
  };

  const confirm = () => {
    return new Promise<T | ConfirmModalDefaultValues>((resolve) => {
      if (dontShowAgain.value) {
        resolve("close");
        return;
      }

      modalContinuePromise.value = resolve;
      isConfirmOpen.value = true;
    });
  };

  provide<ConfirmModalInjectionData<T>>(name, {
    isModalOpen: isConfirmOpen,
    handleClose: handleConfirmClose,
    handleCancel: handleConfirmCancel,
    handleContinue: handleConfirmContinue,
    handleValue,
    dontShowAgain,
  });

  return {
    confirm,
    isConfirmOpen,
    handleConfirmClose,
    handleConfirmCancel,
    handleConfirmContinue,
    handleValue,
    dontShowAgain,
  };
}
