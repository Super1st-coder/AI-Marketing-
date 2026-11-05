<script setup lang="ts">
import type { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import { getGroupChannelStyles } from "@/constants/campaigns";
import { UnidentifiedError } from "@/services/common-errors";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import CampaignsApi, {
  CampaignChannelGroupData,
  CampaignData,
} from "@/services/projects/CampaignsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";
import FunnelFlowValidatorApi from "@/services/funnel-flow/FunnelFlowValidatorApi";
import { toTypedSchema } from "@vee-validate/yup";
import { number, object } from "yup";

const { t } = useI18n();
const router = useRouter();
const brandId = useBrandId();

const isOpen = defineModel<boolean>({ required: true });
const displayNotReadyMessage = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      projectId: number().required(t("forms.required-field")),
      campaignId: number().required(t("forms.required-field")),
      channelGroupId: number().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, resetForm, values, setFieldValue, isSubmitting } =
  useFormWithErrorScrolling({
    validationSchema: schema,
  });

// Fetch all projects of the brand
const allProjects = await fetchAllItems((range) =>
  ProjectsApi.getList(brandId, {
    range,
    order: { updatedAt: "desc" },
  }),
);

// Pre-fetch campaigns and validators for all projects
const projectCampaignsMap = ref<Map<number, CampaignData[]>>(new Map());
// Map of campaignId -> validator results (to check if channels are ready)
const campaignValidatorMap = ref<
  Map<
    number,
    Awaited<
      ReturnType<typeof FunnelFlowValidatorApi.getValidatorResults>
    > | null
  >
>(new Map());
// Set of campaign IDs that have at least one ready channel
const campaignsWithReadyChannels = ref<Set<number>>(new Set());
const isInitialLoading = ref(true);

// Check if a campaign has a ready Paid Social channel
const checkCampaignHasReadyChannel = (
  validator: Awaited<
    ReturnType<typeof FunnelFlowValidatorApi.getValidatorResults>
  > | null,
): boolean => {
  if (!validator) return false;
  const launchpadStep = validator.data.state.find(
    (step) => step.step === "launchpad",
  );
  return launchpadStep?.completed ?? false;
};

// Fetch campaigns and validators for all projects on mount
const initializeProjectCampaigns = async () => {
  for (const project of allProjects) {
    const campaigns = await fetchAllItems((range) =>
      CampaignsApi.getList(brandId, project.id, {
        range,
        order: { updatedAt: "desc" },
      }),
    );
    projectCampaignsMap.value.set(project.id, campaigns);

    // For each complete campaign, check if it has ready channels
    for (const campaign of campaigns) {
      if (campaign.complete) {
        try {
          const validator = await FunnelFlowValidatorApi.getValidatorResults(
            campaign.id,
          );
          campaignValidatorMap.value.set(campaign.id, validator);
          if (checkCampaignHasReadyChannel(validator)) {
            campaignsWithReadyChannels.value.add(campaign.id);
          }
        } catch (e: unknown) {
          console.error(e);
          campaignValidatorMap.value.set(campaign.id, null);
        }
      }
    }
  }
  isInitialLoading.value = false;
};

// Start fetching campaigns
initializeProjectCampaigns();

// Filter projects to only show those with at least one campaign with ready channels
const projectsWithReadyChannels = computed(() =>
  allProjects.filter((project) => {
    const campaigns = projectCampaignsMap.value.get(project.id);
    return campaigns?.some(
      (campaign) =>
        campaign.complete && campaignsWithReadyChannels.value.has(campaign.id),
    );
  }),
);

// Options for the project select field - only projects with ready channels
const projectOptions = computed<AutocompleteOption[]>(() =>
  projectsWithReadyChannels.value.map((project) => ({
    label: project.name,
    value: project.id,
  })),
);

// List of campaigns for selected project
const campaignList = computed(() =>
  values.projectId
    ? projectCampaignsMap.value.get(values.projectId)
    : undefined,
);

// Options for the campaign select field - only campaigns with ready channels
const campaignOptions = computed<AutocompleteOption[]>(() =>
  campaignList.value
    ? campaignList.value
        .filter(
          (campaign) =>
            campaign.complete &&
            campaignsWithReadyChannels.value.has(campaign.id),
        )
        .map((campaign) => ({
          label: campaign.name,
          value: campaign.id,
        }))
    : [],
);

// List of funnel flows
const areChannelGroupsLoading = ref(false);
const channelGroupList = ref<CampaignChannelGroupData[]>();
const validatorResults = ref<Awaited<
  ReturnType<typeof FunnelFlowValidatorApi.getValidatorResults>
> | null>(null);

// Check if a channel group is ready for launch
const isChannelGroupReady = (channelGroupName: string): boolean => {
  // For Paid Social, check the launchpad step in validator
  if (
    channelGroupName === PAID_SOCIAL_CHANNEL_GROUP_NAME &&
    validatorResults.value
  ) {
    const launchpadStep = validatorResults.value.data.state.find(
      (step) => step.step === "launchpad",
    );
    return launchpadStep?.completed ?? false;
  }
  // For other channels, assume ready if they exist
  return true;
};

// Options for the channel group select field - only show ready channels
const channelGroupOptions = computed<AutocompleteOption[]>(() =>
  channelGroupList.value
    ? channelGroupList.value
        .filter(
          (channelGroup) =>
            getGroupChannelStyles(channelGroup.name).availableInFunnelFlow &&
            isChannelGroupReady(channelGroup.name),
        )
        .map((channelGroup) => ({
          label: channelGroup.name,
          value: channelGroup.id,
        }))
    : [],
);

// Clear campaign selection when project changes
watch(
  () => values.projectId,
  () => {
    setFieldValue("campaignId", undefined, false);
  },
);

// Fetch channel groups and validator results
watch(
  () => values.campaignId,
  async (campaignId) => {
    // Clear channel groups and validator
    channelGroupList.value = undefined;
    validatorResults.value = null;
    setFieldValue("channelGroupId", undefined, false);

    if (campaignId) {
      // Fetch channel groups and validator in parallel
      areChannelGroupsLoading.value = true;
      const [channelGroupResponse, validatorResponse] = await Promise.all([
        AdStructureApi.getChannelGroupList(brandId, campaignId),
        FunnelFlowValidatorApi.getValidatorResults(campaignId).catch(
          () => null,
        ),
      ]);
      channelGroupList.value = channelGroupResponse.data.channel_group;
      validatorResults.value = validatorResponse;
      areChannelGroupsLoading.value = false;
    }
  },
);

const selectedCampaign = computed(() =>
  campaignList.value?.find((campaign) => campaign.id === values.campaignId),
);

const selectedChannelGroup = computed(() =>
  channelGroupList.value?.find(
    (channelGroup) => channelGroup.id === values.channelGroupId,
  ),
);

const targetStep = ref<string | undefined>("launchpad");

const selectedChannelGroupRoute = computed(() => {
  const channel = selectedChannelGroup.value;

  if (channel) {
    const route = getGroupChannelStyles(channel.name).route;

    if (route) {
      if (typeof route === "string") {
        return route;
      }

      return {
        ...route,
        params: {
          ...("params" in route ? route.params : {}),
          brandId,
          projectId: values.projectId,
          campaignId: values.campaignId,
        },
        query: { initialStep: targetStep.value },
      };
    }
  }

  return undefined;
});

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  // Check if the route is valid
  if (!selectedChannelGroupRoute.value) {
    throw new UnidentifiedError();
  }

  // Only check if the flow is paid social
  const isPaidSocial =
    selectedChannelGroup.value?.name === PAID_SOCIAL_CHANNEL_GROUP_NAME;

  if (isPaidSocial) {
    // Use the backend validator API (single call instead of multiple)
    const { data: validation } =
      await FunnelFlowValidatorApi.getValidatorResults(values.campaignId);

    // Check if the launchpad step is ready
    const launchpadStep = validation.state.find(
      (step) => step.step === "launchpad",
    );
    const isLaunchpadReady = launchpadStep?.completed ?? false;

    if (!isLaunchpadReady) {
      // The launchpad is not ready - set targetStep to undefined,
      // the paid social form will auto-redirect to the first incomplete step
      targetStep.value = undefined;
      displayNotReadyMessage.value = true;
      return;
    }

    // Launchpad is ready - set target step to launchpad
    targetStep.value = "launchpad";
  }

  // Navigate to channel group
  router.push(selectedChannelGroupRoute.value);
});

// Reset form when modal is closed
watch(
  () => isOpen.value,
  (isOpen) => {
    if (!isOpen) {
      resetForm();
    }
  },
);
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("brands.home.go-to-launchpad-modal.title") }}

      <template #description>
        {{ $t("brands.home.go-to-launchpad-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldAutocomplete
          name="projectId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-launchpad-modal.project.label')"
          :placeholder="
            t('brands.home.go-to-launchpad-modal.project.placeholder')
          "
          :options="projectOptions"
          :loading="isInitialLoading"
        />

        <FieldAutocomplete
          v-if="values.projectId"
          name="campaignId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-launchpad-modal.campaign.label')"
          :placeholder="
            t('brands.home.go-to-launchpad-modal.campaign.placeholder')
          "
          :options="campaignOptions"
        />

        <FieldAutocomplete
          v-if="values.campaignId"
          name="channelGroupId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-launchpad-modal.channel-group.label')"
          :placeholder="
            t('brands.home.go-to-launchpad-modal.channel-group.placeholder')
          "
          :options="channelGroupOptions"
          :loading="areChannelGroupsLoading"
        />

        <Alert
          v-if="displayNotReadyMessage && selectedChannelGroup"
          type="error"
          autoScroll
        >
          <i18n-t
            keypath="brands.home.go-to-launchpad-modal.not-ready-error.text"
          >
            <template #channelGroup>
              <strong>{{ selectedChannelGroup?.name }}</strong>
            </template>

            <template #campaign>
              <strong>{{ selectedCampaign?.name }}</strong>
            </template>

            <template #clickHere>
              <Link
                underline
                color="error"
                :to="
                  selectedChannelGroupRoute
                    ? selectedChannelGroupRoute
                    : undefined
                "
              >
                {{
                  $t(
                    "brands.home.go-to-launchpad-modal.not-ready-error.click-here",
                  )
                }}
              </Link>
            </template>
          </i18n-t>
        </Alert>
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" @click="close" type="button">
        {{ $t("global.cancel") }}
      </Button>
      <Button :isLoading="isSubmitting">
        {{ $t("brands.home.go-to-launchpad-modal.submit") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
