import BuyerPersonasApi from "@/services/BuyerPersonasApi";
import NewBrandsApi, { BrandData } from "@/services/NewBrandsApi";
import ProductsApi from "@/services/ProductsApi";
import CampaignsApi from "@/services/projects/CampaignsApi";
import ProjectsApi, { ProyectData } from "@/services/projects/ProjectsApi";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";

export const useBrandLayoutStore = defineStore("BrandLayoutStore", () => {
  const brand = ref<BrandData>();

  let areProjectsDisabled = ref(true);
  let areUmbrellaCampaignsDisabled = ref(true);
  let areCampaignsDisabled = ref(true);
  let areFunnelFlowsDisabled = ref(true);
  let isLaunchpadDisabled = ref(true);

  const initialize = async (brandId: number) => {
    brand.value = (await NewBrandsApi.getById(brandId)).data;

    // Reset all variables to disabled state
    areProjectsDisabled.value = true;
    areUmbrellaCampaignsDisabled.value = true;
    areCampaignsDisabled.value = true;
    areFunnelFlowsDisabled.value = true;
    isLaunchpadDisabled.value = true;

    // Fetch a single product
    const {
      data: [firstProduct],
    } = await ProductsApi.getList(brandId, {
      range: [0],
    });

    // Fetch a single target customer
    const {
      data: [firstTargetCustomer],
    } = await BuyerPersonasApi.getList(brandId, {
      range: [0],
    });

    // Projects are disabled if there aren't at least one product and one target customer
    areProjectsDisabled.value =
      firstProduct === undefined || firstTargetCustomer === undefined;

    // Since projects are disabled, leave everything else from here disabled
    if (areProjectsDisabled.value) {
      return;
    }

    // Fetch a single project
    const {
      data: [firstProject],
    } = await ProjectsApi.getList(brandId, {
      range: [0],
    });

    // Umbrella campaigns are disabled if there isn't at least one project
    areUmbrellaCampaignsDisabled.value = firstProject === undefined;

    // Since umbrella campaigns are disabled, leave everything else from here disabled
    if (areUmbrellaCampaignsDisabled.value) {
      return;
    }

    // Fetch all projects of the brand
    const allProjects = ref<ProyectData[]>(
      await fetchAllItems((range) =>
        ProjectsApi.getList(brandId, {
          range,
          order: { updatedAt: "desc" },
        }),
      ),
    );

    // Campaigns are disabled if there isn't at least one umbrella campaign in some project
    for (const project of allProjects.value) {
      // Fetch a single umbrella campaign
      const {
        data: [firstUmbrellaCampaign],
      } = await UmbrellaCampaignsApi.getList(brandId, project.id, {
        range: [0],
      });

      // We found an umbrella campaign
      if (firstUmbrellaCampaign) {
        areCampaignsDisabled.value = false;
        break;
      }
    }

    // Since campaigns are disabled, leave everything else from here disabled
    if (areCampaignsDisabled.value) {
      return;
    }

    // Funnel Flows are disabled if there isn't at least one campaign in some project
    // Launchpad is disabled if there isn't at least one COMPLETE campaign
    for (const project of allProjects.value) {
      // Fetch campaigns for this project
      const { data: campaigns } = await CampaignsApi.getList(
        brandId,
        project.id,
        {
          range: [0, 49],
        },
      );

      // We found at least one campaign - enable funnel flows
      if (campaigns.length > 0) {
        areFunnelFlowsDisabled.value = false;
      }

      // Check if any campaign is complete - enable launchpad
      const hasCompleteCampaign = campaigns.some(
        (campaign) => campaign.complete,
      );
      if (hasCompleteCampaign) {
        isLaunchpadDisabled.value = false;
      }

      // If both are enabled, we can stop checking
      if (!areFunnelFlowsDisabled.value && !isLaunchpadDisabled.value) {
        break;
      }
    }
  };

  return {
    brand,
    initialize,
    areProjectsDisabled,
    areUmbrellaCampaignsDisabled,
    areCampaignsDisabled,
    areFunnelFlowsDisabled,
    isLaunchpadDisabled,
  };
});
