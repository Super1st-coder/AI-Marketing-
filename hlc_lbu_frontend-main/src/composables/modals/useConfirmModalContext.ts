import {
  ConfirmModalDefaultValues,
  ConfirmModalInjectionData,
} from "./useConfirmModal";

export function useConfirmModalContext<T = ConfirmModalDefaultValues>(
  name: string = "confirm",
) {
  const data = inject<ConfirmModalInjectionData<T>>(name)!;

  return data;
}
