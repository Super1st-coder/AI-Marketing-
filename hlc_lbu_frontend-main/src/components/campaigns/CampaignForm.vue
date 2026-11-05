<script setup lang="ts">
import { CampaignData } from "@/services/projects/CampaignsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";

export type CampaignFormData = CampaignData;

const props = defineProps<{
  data?: CampaignFormData;
}>();
const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;
const authStore = useAuthStore();

const userHas = (step: FormStep) => {
  if (!step.requires) return true;

  return authStore.hasPermissionFor(step.requires);
};

const steps = computed<FormStep[]>(() => [
  {
    name: "information",
    label: t("campaigns.sidebarmenu.informationlabel"),
    icon: "tabler-book",
    requires: [{ name: "CAMPAIGN_SETUP", actions: ["R", "C", "U"] }],
  },
  {
    name: "umbrellaCampaign",
    label: t("campaigns.sidebarmenu.umbrellacampaignlabel"),
    icon: "tabler-palette",
    requires: [{ name: "CAMPAIGN_SETUP", actions: ["R", "C", "U"] }],
  },
  {
    name: "funnel",
    label: t("campaigns.sidebarmenu.funnellabel"),
    icon: "tabler-filter",
    requires: [{ name: "CAMPAIGN_SETUP", actions: ["R", "C", "U"] }],
  },
  {
    name: "kpis",
    label: t("campaigns.sidebarmenu.kpislabel"),
    icon: "tabler-file-report",
    children: [
      {
        name: "channels",
        label: t("campaigns.stepper.kpis.channels"),
      },
      {
        name: "metrics",
        label: t("campaigns.stepper.kpis.metrics"),
      },
    ],
    requires: [{ name: "CAMPAIGN_SETUP", actions: ["R", "C", "U"] }],
  },
  {
    name: "concept",
    label: t("campaigns.sidebarmenu.conceptlabel"),
    icon: "tabler-medal",
    requires: [{ name: "CAMPAIGN_CREATIVE", actions: ["R", "C", "U"] }],
    children: [
      {
        name: "tutorial",
        label: t("campaigns.stepper.concept.tutorial"),
      },
      {
        name: "bigIdea",
        label: t("campaigns.stepper.concept.big-idea"),
      },
      {
        name: "timing",
        label: t("campaigns.stepper.concept.timing"),
      },
      {
        name: "messageLocation",
        label: t("campaigns.stepper.concept.message-location"),
      },
      {
        name: "audienceExperience",
        label: t("campaigns.stepper.concept.audience-experience"),
      },
      {
        name: "tools",
        label: t("campaigns.stepper.concept.tools"),
      },
      {
        name: "productDetails",
        label: t("campaigns.stepper.concept.product-details"),
      },
      {
        name: "buyerPersonDetails",
        label: t("campaigns.stepper.concept.buyer-person-details"),
      },
      {
        name: "selectCampaign",
        label: t("campaigns.stepper.concept.select-campaign"),
      },
    ],
  },
  {
    name: "image",
    label: t("campaigns.sidebarmenu.imagelabel"),
    icon: "tabler-photo",
    requires: [{ name: "CAMPAIGN_CREATIVE", actions: ["R", "C", "U"] }],
  },
  {
    name: "summary",
    label: t("campaigns.sidebarmenu.summarylabel"),
    icon: "tabler-file-text",
    requires: [
      { name: "CAMPAIGN_CREATIVE", actions: ["R"] },
      { name: "CAMPAIGN_SETUP", actions: ["R"] },
    ],
  },
]);

const initialStep = computed<number>(() => {
  // Values of "step":
  // 0 - Define
  // 0 - Update
  // 1 - Set Creative Concept
  // 2 - Set Funnel
  // 3 - Set Channel Group
  // 4 - Save Metrics
  // 5 - Set Big Idea
  // 6 - Set Timing
  // 7 - Set Message Location
  // 8 - Set Audience Experience
  // 9 - Set Tools
  // 10 - Set Product Details
  // 11 - Set Buyer Person Details
  // 12 - Save Generated Campaigns
  // 12 - Set Preferred Campaign
  // 13 - Generate Summary
  // 14 - Set Image Style
  // 15 - Generate Image Attributes
  // 15 - Save Image Attributes
  // 16 - Generate Image Prompts
  // 16 - Set Preferred Image Prompt
  // 16 - Save Preferred Image Prompt
  // 17 - Upload image
  // 18 - Save Summary

  if (props.data?.step != undefined) {
    switch (props.data.step) {
      case 0:
        return 1;
      case 1:
        return 2;
      case 2:
        return 3;
      case 3:
        return 4;
      case 4:
        return 6;
      case 5:
        return 7;
      case 6:
        return 8;
      case 7:
        return 9;
      case 8:
        return 10;
      case 9:
        return 11;
      case 10:
        return 12;
      case 11:
        return 13;
      case 12:
        return 13;
      case 13:
        return 14;
      case 14:
        return 14;
      case 15:
        return 14;
      case 16:
        return 14;
      case 17:
        return 15;
      case 18:
        return 15;
      default:
        return 0;
    }
  }

  return 0;
});

// Initialize the multi-step form
const { data } = useMultiStepForm(steps, {
  useLocalStorage: true,
  initialData: props.data,
  initialStep: initialStep,
  id: (data) => `campaign-${data?.id}`,
  filterStep: (step) => userHas(step),
});
</script>

<template>
  <MultiStepForm>
    <template #sidebarHeader>
      <template v-if="data">
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("campaigns.sidebarmenu.title") }}
        </SidebarTitle>

        <SidebarTitle>
          {{ data.name }}
        </SidebarTitle>
      </template>
      <template v-else>
        <SidebarTitle>
          {{ $t("campaigns.sidebarmenu.createnewcampaign") }}</SidebarTitle
        >
      </template>
    </template>

    <FormStep name="information">
      <CampaignFormInformation />
    </FormStep>

    <FormStep name="umbrellaCampaign">
      <CampaignFormUmbrellaCampaign />
    </FormStep>

    <FormStep name="funnel">
      <CampaignFormFunnel />
    </FormStep>

    <FormStep name="channels">
      <CampaignFormChannels />
    </FormStep>

    <FormStep name="metrics">
      <CampaignFormMetrics />
    </FormStep>

    <FormStep name="tutorial">
      <CampaignFormConceptTutorial />
    </FormStep>

    <FormStep name="bigIdea">
      <CampaignFormConceptBigIdea />
    </FormStep>

    <FormStep name="timing">
      <CampaignFormConceptTiming />
    </FormStep>

    <FormStep name="messageLocation">
      <CampaignFormConceptMessageLocation />
    </FormStep>

    <FormStep name="audienceExperience">
      <CampaignFormConceptAudienceExperience />
    </FormStep>

    <FormStep name="tools">
      <CampaignFormConceptTools />
    </FormStep>

    <FormStep name="productDetails">
      <CampaignFormConceptProduct />
    </FormStep>

    <FormStep name="buyerPersonDetails">
      <CampaignFormConceptBuyerPerson />
    </FormStep>

    <FormStep name="selectCampaign">
      <CampaignFormConceptSelectCampaign />
    </FormStep>

    <FormStep name="image">
      <CampaignFormImage />
    </FormStep>

    <FormStep name="summary">
      <CampaignFormSummary />
    </FormStep>

    <template #sidebarFooter>
      <SidebarLink
        :to="{ name: 'CampaignList' }"
        variant="link"
        icon="tabler-arrow-left"
      >
        {{ $t("projects.back-to-project", { name: project.name }) }}
      </SidebarLink>
    </template>
  </MultiStepForm>
</template>
