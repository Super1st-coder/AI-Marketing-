import { useRouteQuery } from "@vueuse/router";
import { RouteLocationRaw } from "vue-router";

export default function useProjectQueryShorcut() {
  const targetProjectId = useRouteQuery("projectId", undefined, {
    transform: optionalNumber,
  });
  const targetProjectStep = useRouteQuery("projectStep", 0, {
    transform: optionalNumber,
  });

  const targetProjectRoute = computed<RouteLocationRaw | undefined>(() => {
    if (
      targetProjectId.value != undefined &&
      targetProjectStep.value != undefined
    ) {
      return {
        name: "ProjectSettings",
        params: {
          projectId: targetProjectId.value,
        },
      };
    }

    return undefined;
  });

  return { targetProjectId, targetProjectStep, targetProjectRoute };
}
