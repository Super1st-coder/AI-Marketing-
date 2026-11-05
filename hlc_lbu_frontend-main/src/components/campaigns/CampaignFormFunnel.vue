<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { number, object } from "yup";
import { CampaignFormData } from "./CampaignForm.vue";
import CampaignsApi from "@/services/projects/CampaignsApi";
import UtilsApi from "@/services/UtilsApi";

const brandId = useBrandId();
const projectId = useProjectId();

const { data: funnelList } = await UtilsApi.getFunnelList();

const funnels = [...funnelList].sort(
  (a, b) => Number(b.active) - Number(a.active),
);

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<CampaignFormData>();

// const isSurveyOpen = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      funnelId: number().required("Please select one funnel to continue."),
    }),
  ),
);

const { handleSubmit, isSubmitting, setFieldValue, errors, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      funnelId: data.value.funnel?.id,
    },
  });

// Promise resolve function used when the survey modal is closed
// const surveyPromise = ref<(value: true) => void>();
// watch(isSurveyOpen, (isOpen) => {
//   if (!isOpen) {
//     surveyPromise.value?.(true);
//   }
// });
// const openSurvey = () => {
//   return new Promise<boolean>((resolve) => {
//     surveyPromise.value = resolve;
//     isSurveyOpen.value = true;
//   });
// };

const onSubmit = handleSubmit(async (values) => {
  // Wait fo the survey modal
  // await openSurvey();

  let response = await CampaignsApi.setFunnelId(
    brandId,
    projectId,
    data.value.id,
    values.funnelId,
  );

  // Save data and go next
  saveData({
    ...response.data,
  });
  goNext();
});

const handleSelect = (funnelId: number) => {
  const funnel = funnels.find((funnel) => funnel.id === funnelId);
  if (funnel?.active === false) {
    return;
  }

  setFieldValue("funnelId", funnelId);
};

const images = {
  Awareness: "/images/emojis/emoji-brain.png",
  Acquisition: "/images/emojis/emoji-shopping-bags.png",
  Activation: "/images/emojis/emoji-high-voltage.png",
  Retention: "/images/emojis/emoji-floppy-disk.png",
  Revenue: "/images/emojis/emoji-money-bag.png",
  Referral: "/images/emojis/emoji-handshake.png",
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <!-- TODO: add help video URL later -->
    <PageTitle>
      {{ $t("campaigns.funnel.title") }}
      <template #description>
        {{ $t("campaigns.funnel.description") }}
      </template>
    </PageTitle>

    <div class="tw:grid tw:gap-6 tw:md:grid-cols-2 tw:lg:grid-cols-3">
      <CampaignFormFunnelCard
        v-for="funnel in funnels"
        name="funnelId"
        :funnel="funnel"
        :imageSrc="images[funnel.name]"
        @click="handleSelect(funnel.id)"
      />
    </div>

    <Alert v-if="errors.funnelId" type="error">
      {{ errors.funnelId }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
    <!-- <CampaignFormFunnelSurveyModal v-model="isSurveyOpen" /> -->
  </FormStepLayout>
</template>
