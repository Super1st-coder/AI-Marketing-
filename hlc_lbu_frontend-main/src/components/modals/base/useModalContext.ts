export type ModalScrollable = "outer" | "inner";

export const modalScrollableInjectionKey = Symbol(
  "modalScrollable",
) as InjectionKey<ComputedRef<ModalScrollable>>;
