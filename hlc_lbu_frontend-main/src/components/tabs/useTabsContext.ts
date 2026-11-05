type TabsValueInjectionData = {
  current: Ref<string | number | undefined>;
  variant: ComputedRef<"default" | "buttonGroup">;
  alignment: ComputedRef<"start" | "center" | "end">;
  size: ComputedRef<"sm" | "lg">;
  keepOnUnmount: ComputedRef<boolean>;
};

export const tabsValueInjectionKey = Symbol(
  "tabsValue",
) as InjectionKey<TabsValueInjectionData>;

export function useTabsContext() {
  const data = inject<TabsValueInjectionData>(tabsValueInjectionKey);

  return data;
}
