import { breakpointsTailwind } from "@vueuse/core";
import { MaybeRef } from "vue";

export function useMaxHeightCards(
  selectors: MaybeRef<string[]>,
  dependencies: any[],
) {
  const breakpoints = useBreakpoints(breakpointsTailwind);
  const isMaxHeightEnabled = breakpoints.greaterOrEqual("lg");
  const { recalculateHeight } = useMaxHeight(selectors, isMaxHeightEnabled);

  // Update the height when the values of the form are updated
  dependencies.forEach((dependency) => {
    watch(dependency, async () => {
      await nextTick();
      recalculateHeight();
    });
  });

  return { recalculateHeight };
}
