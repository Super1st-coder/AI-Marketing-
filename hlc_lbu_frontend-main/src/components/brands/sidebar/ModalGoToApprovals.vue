<script setup lang="ts">
import type { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import { getGroupChannelStyles } from "@/constants/campaigns";
import { UnidentifiedError } from "@/services/common-errors";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import CampaignsApi, {
  CampaignChannelGroupData,
  CampaignData,
} from "@/services/projects/CampaignsApi";
import ProjectsApi, { ProyectData } from "@/services/projects/ProjectsApi";
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
const projectsList = ref<ProyectData[]>(
  await fetchAllItems((range) =>
    ProjectsApi.getList(brandId, {
      range,
      order: { updatedAt: "desc" },
    }),
  ),
);

// Options for the project select field
const projectOptions = computed<AutocompleteOption[]>(() =>
  [...projectsList.value]
    .sort((a, b) => Number(b.status === "A") - Number(a.status === "A"))
    .map((project) => ({
      label: project.name,
      value: project.id,
      disabled: project.status !== "A",
      chip:
        project.status !== "A"
          ? {
              label: t("global.incomplete"),
              color: "error",
              variant: "label",
            }
          : undefined,
    })),
);

// List of campaigns
const areCampaignsLoading = ref(false);
const campaignList = ref<CampaignData[]>();

// Options for the campaign select field
const campaignOptions = computed<AutocompleteOption[]>(() =>
  campaignList.value
    ? [...campaignList.value]
        .sort((a, b) => Number(b.complete) - Number(a.complete))
        .map((campaign) => ({
          label: campaign.name,
          value: campaign.id,
          disabled: !campaign.complete,
          chip: !campaign.complete
            ? {
                label: t("global.incomplete"),
                color: "error",
                variant: "label",
              }
            : undefined,
        }))
    : [],
);

// List of funnel flows
const areChannelGroupsLoading = ref(false);
const channelGroupList = ref<CampaignChannelGroupData[]>();

// Options for the channel group select field
const channelGroupOptions = computed<AutocompleteOption[]>(() =>
  channelGroupList.value
    ? channelGroupList.value
        .filter(
          (channelGroup) =>
            getGroupChannelStyles(channelGroup.name).availableInFunnelFlow,
        )
        .map((channelGroup) => ({
          label: channelGroup.name,
          value: channelGroup.id,
        }))
    : [],
);

// Fetch campaigns
watch(
  () => values.projectId,
  async (projectId) => {
    // Clear campaigns
    campaignList.value = undefined;
    setFieldValue("campaignId", undefined, false);

    if (projectId) {
      // Fetch campaigns
      areCampaignsLoading.value = true;
      campaignList.value = await fetchAllItems((range) =>
        CampaignsApi.getList(brandId, projectId, {
          range,
          order: { updatedAt: "desc" },
        }),
      );
      areCampaignsLoading.value = false;
    }
  },
);

// Fetch channel groups
watch(
  () => values.campaignId,
  async (campaignId) => {
    // Clear channel groups
    channelGroupList.value = undefined;
    setFieldValue("channelGroupId", undefined, false);

    if (campaignId) {
      // Fetch channel groups
      areChannelGroupsLoading.value = true;
      channelGroupList.value = (
        await AdStructureApi.getChannelGroupList(brandId, campaignId)
      ).data.channel_group;
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

const targetStep = ref<string | undefined>("review");

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

    // Check if the review step is ready
    const reviewStep = validation.state.find((step) => step.step === "review");
    const isReviewReady = reviewStep?.completed ?? false;

    if (!isReviewReady) {
      // The review step is not ready - set targetStep to undefined,
      // the paid social form will auto-redirect to the first incomplete step
      targetStep.value = undefined;
      displayNotReadyMessage.value = true;
      return;
    }

    // Review is ready - set target step to review
    targetStep.value = "review";
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
      {{ $t("brands.home.go-to-approvals-modal.title") }}

      <template #description>
        {{ $t("brands.home.go-to-approvals-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldAutocomplete
          name="projectId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-approvals-modal.project.label')"
          :placeholder="
            t('brands.home.go-to-approvals-modal.project.placeholder')
          "
          :options="projectOptions"
        />

        <FieldAutocomplete
          v-if="values.projectId"
          name="campaignId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-approvals-modal.campaign.label')"
          :placeholder="
            t('brands.home.go-to-approvals-modal.campaign.placeholder')
          "
          :options="campaignOptions"
          :loading="areCampaignsLoading"
        />

        <FieldAutocomplete
          v-if="values.campaignId"
          name="channelGroupId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-approvals-modal.channel-group.label')"
          :placeholder="
            t('brands.home.go-to-approvals-modal.channel-group.placeholder')
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
            keypath="brands.home.go-to-approvals-modal.not-ready-error.text"
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
                    "brands.home.go-to-approvals-modal.not-ready-error.click-here",
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
        {{ $t("brands.home.go-to-approvals-modal.submit") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
