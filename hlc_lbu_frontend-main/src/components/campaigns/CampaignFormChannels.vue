<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object } from "yup";
import { CampaignFormData } from "./CampaignForm.vue";
import CampaignsApi from "@/services/projects/CampaignsApi";
import UtilsApi from "@/services/UtilsApi";

const brandId = useBrandId();
const projectId = useProjectId();

const { data: channelGroupList } = await UtilsApi.getChannelGroupList();

const channelGroups = [...channelGroupList].sort(
  (a, b) => Number(b.active) - Number(a.active),
);

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<CampaignFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      channelGroupIds: array()
        .of(number().required())
        .min(1, "Please select at least one channel group to continue.")
        .required(),
    }),
  ),
);

const { handleSubmit, isSubmitting, values, setFieldValue, errors, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      channelGroupIds:
        data.value.channel_group?.map((group) => group.id).flat() ?? [],
    },
  });

const onSubmit = handleSubmit(async (values) => {
  let response = await CampaignsApi.setChannelGroups(
    brandId,
    projectId,
    data.value.id,
    values.channelGroupIds,
  );

  // Save data and go next
  saveData({
    ...response.data,
    // The response doesn't come with the metrics, so we need to add them
    channel_group: response.data.channel_group
      ? response.data.channel_group.map((group) => ({
          ...group,
          // Get the metrics for this group in the stored data
          metrics: data.value.channel_group?.find(
            (_group) => _group.id === group.id,
          )?.metrics,
        }))
      : undefined,
  });
  goNext();
});

const handleSelect = (channelId: number) => {
  if (!values.channelGroupIds) {
    return;
  }

  const group = channelGroups.find((group) => group.id === channelId);
  // Check if the group is active
  if (group?.active === false) {
    return;
  }

  setFieldValue(
    "channelGroupIds",
    values.channelGroupIds.includes(channelId)
      ? values.channelGroupIds.filter((id) => id !== channelId)
      : [...values.channelGroupIds, channelId],
  );
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="kpis" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=21WcOjHaT-M"
    >
      {{ $t("campaigns.channels.title") }}
      <template #description>
        {{ $t("campaigns.channels.description") }}
      </template>
    </PageTitle>

    <div class="tw:grid tw:gap-6 tw:md:grid-cols-2 tw:lg:grid-cols-3">
      <CampaignFormChannelCard
        v-for="channelGroup in channelGroups"
        name="channelGroupIds"
        :channelGroup="channelGroup"
        @click="handleSelect(channelGroup.id)"
      />
    </div>

    <Alert v-if="errors.channelGroupIds" type="error">
      {{ errors.channelGroupIds }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
