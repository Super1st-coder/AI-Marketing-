import { useRouteQuery } from "@vueuse/router";
import { RouteLocationRaw } from "vue-router";

export default function useProjectQueryShorcut() {
  const targetCampaignId = useRouteQuery("campaignId", undefined, {
    transform: optionalNumber,
  });
  const targetCampaignStep = useRouteQuery("campaignStep", 0, {
    transform: optionalNumber,
  });

  const targetCampaignRoute = computed<RouteLocationRaw | undefined>(() => {
    if (
      targetCampaignId.value != undefined &&
      targetCampaignStep.value != undefined
    ) {
      return {
        name: "CampaignSettings",
        params: {
          campaignId: targetCampaignId.value,
        },
      };
    }

    return undefined;
  });

  return { targetCampaignId, targetCampaignStep, targetCampaignRoute };
}
