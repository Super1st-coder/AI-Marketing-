<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object } from "yup";
import { FunnelPaidSocialFormData } from "../FunnelPaidSocialForm.vue";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";

const { data, goNext, goBack } =
  useMultiStepFormContext<FunnelPaidSocialFormData>();

const schema = computed(() => toTypedSchema(object({})));

const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {},
});

const onSubmit = handleSubmit(async (formValues) => {
  console.log("Form values:", formValues);
  goNext();
});

const brandId = useBrandId();
const campaignId = useCampaignId();

const { data: adStructureData } =
  await AdStructureApi.getAdStructureByChannelGroup(brandId, campaignId, 2);

const adSets = adStructureData.ad_sets;
</script>

<template>
  <FunnelPaidSocialFormSideBar
    :title="data.campaign.name"
    :adSets="adSets"
    :adSetsClickeables="false"
    :adsClickeables="false"
  >
    <FormStepLayout @submit.prevent="onSubmit">
      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=pMjiVJB0Yls"
      >
        {{ $t("audience.title") }}
      </PageTitle>

      <div class="tw:flex tw:justify-center">
        <CardBase
          class="tw:flex tw:w-full tw:flex-col tw:gap-6 tw:p-5 tw:lg:w-1/2"
        >
          <h3 class="tw:text-center tw:text-lg tw:font-extrabold">
            {{ $t("audience.define-audience-title") }}
          </h3>

          <p>
            {{ $t("audience.define-audience-description") }}
          </p>

          <div class="tw:grid tw:grid-cols-2 tw:gap-5">
            <Button size="md" class="tw:w-full" type="button" @click="goNext">
              {{ $t("audience.define-audience-opt-1") }}
            </Button>
            <Button disabled size="md" class="tw:w-full" type="button">
              {{ $t("audience.define-audience-opt-2") }}
              <div
                class="tw:absolute tw:-top-2 tw:-right-2 tw:rounded-md tw:bg-secondary tw:px-2 tw:py-1 tw:text-xs tw:font-bold tw:capitalize"
              >
                {{ $t("global.soon") }}
              </div>
            </Button>
          </div>
        </CardBase>
      </div>

      <template #actions>
        <WizardCardActions>
          <ButtonGoBack @click="goBack" />
          <ButtonNext :isLoading="isSubmitting" />
        </WizardCardActions>
      </template>
    </FormStepLayout>
  </FunnelPaidSocialFormSideBar>
</template>
