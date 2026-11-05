import { MultiStepFormInjectionData } from "./useMultiStepForm";

export function useMultiStepFormContext<T>() {
  const data = inject(
    multiStepFormInjectionKey as InjectionKey<MultiStepFormInjectionData<T>>,
  )!;
  return data;
}
