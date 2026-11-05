export type AccordionVariant = "default" | "solid" | "text" | "card";

export type AccordionListInjectionData = {
  variant: ComputedRef<AccordionVariant>;
};

export const accordionListInjectionKey =
  Symbol() as InjectionKey<AccordionListInjectionData>;

export function useAccordionContext() {
  const data = inject<AccordionListInjectionData>(accordionListInjectionKey, {
    variant: computed(() => "default"),
  });

  return data;
}
