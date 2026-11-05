<script setup lang="ts">
import CampaignsApi from "@/services/projects/CampaignsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";
import { UmbrellaCampaignData } from "@/services/projects/UmbrellaCampaignsApi";

export type UmbrellaCampaignFormData = UmbrellaCampaignData;

const props = defineProps<{
  data?: UmbrellaCampaignFormData;
}>();
const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;

const { targetCampaignId, targetCampaignRoute } = useCampaignQueryShorcut();
const targetCampaign = targetCampaignId.value
  ? (await CampaignsApi.getOne(brandId, projectId, targetCampaignId.value)).data
  : undefined;
const authStore = useAuthStore();

const userHas = (step: FormStep) => {
  if (!step.requires) return true;

  return authStore.hasPermissionFor(step.requires);
};

const steps = computed<FormStep[]>(() => [
  {
    name: "information",
    label: t("umbrella-campaign.form.steps.information"),
    icon: "tabler-book",
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R", "C", "U"] }],
  },
  {
    name: "bigIdea",
    label: t("umbrella-campaign.form.steps.create-big-idea"),
    icon: "tabler-star",
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R", "C", "U"] }],
    children: [
      {
        name: "ideaTutorial",
        label: t("umbrella-campaign.form.stepper.big-idea.tutorial"),
      },
      {
        name: "idea",
        label: t("umbrella-campaign.form.stepper.big-idea.idea"),
      },
    ],
  },
  {
    name: "benefit",
    label: t("umbrella-campaign.form.steps.benefit"),
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R", "C", "U"] }],
    icon: "tabler-comet",
    children: [
      {
        name: "benefitTutorial",
        label: t("umbrella-campaign.form.stepper.benefit.tutorial"),
      },
      {
        name: "benefitResources",
        label: t("umbrella-campaign.form.stepper.benefit.resources"),
      },
      {
        name: "benefitCustomer",
        label: t("umbrella-campaign.form.stepper.benefit.customer"),
      },
    ],
  },
  {
    name: "drama",
    label: t("umbrella-campaign.form.steps.drama"),
    icon: "tabler-cloud-rain",
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R", "C", "U"] }],
    children: [
      {
        name: "dramaTutorial",
        label: t("umbrella-campaign.form.stepper.drama.tutorial"),
      },
      {
        name: "dramaMotivesAndBarriers",
        label: t("umbrella-campaign.form.stepper.drama.motives-and-barriers"),
      },
      {
        name: "dramaSelection",
        label: t("umbrella-campaign.form.stepper.drama.selection"),
      },
    ],
  },
  {
    name: "scene",
    label: t("umbrella-campaign.form.steps.scene"),
    icon: "tabler-frame",
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R", "C", "U"] }],
    children: [
      {
        name: "sceneTutorial",
        label: t("umbrella-campaign.form.stepper.scene.tutorial"),
      },
      {
        name: "sceneStages",
        label: t("umbrella-campaign.form.stepper.scene.stages"),
      },
      {
        name: "sceneSelection",
        label: t("umbrella-campaign.form.stepper.scene.selection"),
      },
    ],
  },
  {
    name: "selection",
    label: t("umbrella-campaign.form.steps.select"),
    icon: "tabler-umbrella",
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R", "C", "U"] }],
  },
  {
    name: "image",
    label: t("umbrella-campaign.form.steps.image"),
    icon: "tabler-photo",
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R", "C", "U"] }],
  },
  {
    name: "summary",
    label: t("umbrella-campaign.form.steps.summary"),
    icon: "tabler-file-text",
    requires: [{ name: "UMBRELLA_CAMPAIGN", actions: ["R"] }],
  },
]);

const initialStep = computed<number>(() => {
  // Values of "step":
  // 0 - Define
  // 0 - Update
  // 1 - Set Central Idea
  // 2 - Set Buyer Person Resources
  // 3 - Save Generated Benefits
  // 3 - Set Preferred Benefit
  // 4 - Set Buyer Person Motives and Barriers
  // 5 - Save Generated Dramas
  // 5 - Set Preferred Drama
  // 6 - Set Story Stages
  // 7 - Save Generated Scenes
  // 7 - Set Preferred Scene
  // 8 - Save Generated Umbrella Campaigns
  // 8 - Set Preferred Umbrella Campaign
  // 9 - Gennerate Summary
  // 10 - Set Image Style
  // 11 - Generate Image Attributes
  // 11 - Save Image Attributes
  // 12 - Generate Image Prompts
  // 12 - Set Preferred Image Prompt
  // 12 - Save Preferred Image Prompt
  // 13 - Upload image
  // 14 - Save Summary

  if (props.data?.step != undefined) {
    switch (props.data.step) {
      case 0:
        return 1;
      case 1:
        return 3;
      case 2:
        return 5;
      case 3:
        return 6;
      case 4:
        return 8;
      case 5:
        return 9;
      case 6:
        return 11;
      case 7:
        return 12;
      case 8:
        return 13;
      case 9:
        return 13;
      case 10:
        return 13;
      case 11:
        return 13;
      case 12:
        return 13;
      case 13:
        return 14;
      case 14:
        return 14;
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
  id: (data) => `umbrella-campaign-${data?.id}`,
  filterStep: (step) => userHas(step),
});
</script>

<template>
  <MultiStepForm>
    <template #sidebarHeader>
      <template v-if="data">
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("umbrella-campaign.form.sidebar-title") }}
        </SidebarTitle>

        <SidebarTitle>
          {{ data.name }}
        </SidebarTitle>
      </template>
      <template v-else>
        <SidebarTitle>
          {{ $t("umbrella-campaign.form.sidebar-title-create") }}
        </SidebarTitle>
      </template>
    </template>

    <template #sidebarFooter>
      <SidebarLink
        v-if="targetCampaign && targetCampaignRoute"
        :to="targetCampaignRoute"
        variant="link"
        icon="tabler-arrow-left"
        replace
      >
        {{
          $t("campaigns.back-to-campaign-with-name", {
            name: targetCampaign.name,
          })
        }}
      </SidebarLink>
      <SidebarLink
        v-else
        :to="{ name: 'UmbrellaCampaignList' }"
        variant="link"
        icon="tabler-arrow-left"
      >
        {{ $t("projects.back-to-project", { name: project.name }) }}
      </SidebarLink>
    </template>

    <FormStep name="information">
      <UmbrellaCampaignFormInformation />
    </FormStep>

    <FormStep name="ideaTutorial">
      <UmbrellaCampaignFormIdeaTutorial />
    </FormStep>

    <FormStep name="idea">
      <UmbrellaCampaignFormIdea />
    </FormStep>

    <FormStep name="benefitTutorial">
      <UmbrellaCampaignFormBenefitTutorial />
    </FormStep>

    <FormStep name="benefitResources">
      <UmbrellaCampaignFormBenefitResources />
    </FormStep>

    <FormStep name="benefitCustomer">
      <UmbrellaCampaignFormBenefitCustomer />
    </FormStep>

    <FormStep name="dramaTutorial">
      <UmbrellaCampaignFormDramaTutorial />
    </FormStep>

    <FormStep name="dramaMotivesAndBarriers">
      <UmbrellaCampaignFormDramaMotivesAndBarriers />
    </FormStep>

    <FormStep name="dramaSelection">
      <UmbrellaCampaignFormDramaSelection />
    </FormStep>

    <FormStep name="sceneTutorial">
      <UmbrellaCampaignFormSceneTutorial />
    </FormStep>

    <FormStep name="sceneStages">
      <UmbrellaCampaignFormSceneStages />
    </FormStep>

    <FormStep name="sceneSelection">
      <UmbrellaCampaignFormSceneSelection />
    </FormStep>

    <FormStep name="selection">
      <UmbrellaCampaignFormSelection />
    </FormStep>

    <FormStep name="image">
      <UmbrellaCampaignFormImage />
    </FormStep>

    <FormStep name="summary">
      <UmbrellaCampaignFormSummary />
    </FormStep>
  </MultiStepForm>
</template>
