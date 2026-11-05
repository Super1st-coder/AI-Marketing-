<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { UnidentifiedError } from "@/services/common-errors";
import { CampaignFormData } from "./CampaignForm.vue";
import CampaignsApi from "@/services/projects/CampaignsApi";
import { buildMetricsSummaryText } from "./campaignSummaryMetrics";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const { goBack, data } = useMultiStepFormContext<CampaignFormData>();

const showModal = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      bperson: object({
        persona_profile: string().required(t("forms.required-field")).trim(),
        persona_challenges: string().required(t("forms.required-field")).trim(),
        persona_journey: string().required(t("forms.required-field")).trim(),
        persona_motivation: string().required(t("forms.required-field")).trim(),
      }),
      campaign: object({
        campaign_concept_timing: string()
          .required(t("forms.required-field"))
          .trim(),
        campaign_goals: string().required(t("forms.required-field")).trim(),
        campaign_resources: string().required(t("forms.required-field")).trim(),
        campaign_kpis: string().required(t("forms.required-field")).trim(),
      }),
      product: object({
        core_incentive_offer: string()
          .required(t("forms.required-field"))
          .trim(),
        problem_solution_fit: string()
          .required(t("forms.required-field"))
          .trim(),
        unique_value_proposition: string()
          .required(t("forms.required-field"))
          .trim(),
        emotional_outcome_payoff: string()
          .required(t("forms.required-field"))
          .trim(),
      }),
    }),
  ),
);

const { isSubmitting, handleSubmit, meta } = useFormWithErrorScrolling({
  keepValuesOnUnmount: true,
  validationSchema: schema,
  resetDirtyOnSubmit: true,
  initialValues: {
    bperson: {
      persona_profile:
        data.value.summary_saved?.bperson.persona_profile ??
        data.value.summary_generated?.bperson.persona_profile,
      persona_challenges:
        data.value.summary_saved?.bperson.persona_challenges ??
        data.value.summary_generated?.bperson.persona_challenges,
      persona_journey:
        data.value.summary_saved?.bperson.persona_journey ??
        data.value.summary_generated?.bperson.persona_journey,
      persona_motivation:
        data.value.summary_saved?.bperson.persona_motivation ??
        data.value.summary_generated?.bperson.persona_motivation,
    },
    campaign: {
      campaign_concept_timing:
        data.value.summary_saved?.campaign.campaign_concept_timing ??
        data.value.summary_generated?.campaign.campaign_concept_timing,
      campaign_goals:
        data.value.summary_saved?.campaign.campaign_goals ||
        data.value.summary_generated?.campaign.campaign_goals ||
        buildMetricsSummaryText(data.value, "Goals") ||
        "No input data",
      campaign_resources:
        data.value.summary_saved?.campaign.campaign_resources ||
        data.value.summary_generated?.campaign.campaign_resources ||
        buildMetricsSummaryText(data.value, "Resources") ||
        "No input data",
      campaign_kpis:
        data.value.summary_saved?.campaign.campaign_kpis ||
        data.value.summary_generated?.campaign.campaign_kpis ||
        buildMetricsSummaryText(data.value, "Marketing") ||
        "No input data",
    },
    product: {
      core_incentive_offer:
        data.value.summary_saved?.product.core_incentive_offer ??
        data.value.summary_generated?.product.core_incentive_offer,
      problem_solution_fit:
        data.value.summary_saved?.product.problem_solution_fit ??
        data.value.summary_generated?.product.problem_solution_fit,
      unique_value_proposition:
        data.value.summary_saved?.product.unique_value_proposition ??
        data.value.summary_generated?.product.unique_value_proposition,
      emotional_outcome_payoff:
        data.value.summary_saved?.product.emotional_outcome_payoff ??
        data.value.summary_generated?.product.emotional_outcome_payoff,
    },
  },
});

const authStore = useAuthStore();

const handleContinue = handleSubmit(async (values) => {
  if (!data.value.summary_generated) {
    throw new UnidentifiedError();
  }

  await CampaignsApi.SaveSummary(brandId, projectId, data.value.id, {
    summary_generated: {
      ...data.value.summary_generated,
    },
    summary_saved: values,
  });

  showModal.value = true;
});

const handleRedirect = handleSubmit(() => {
  if (!data.value.summary_generated) {
    throw new UnidentifiedError();
  }

  showModal.value = true;
});

const campaignSetupHasUC = computed(() =>
  authStore.hasPermissionFor([{ name: "CAMPAIGN_SETUP", actions: ["U", "C"] }]),
);
</script>

<template>
  <FormStepLayout :disabled="isSubmitting">
    <CampaignFormSummaryModal v-model="showModal" />

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=TKncfcF1xQ0"
    >
      {{
        $t("campaigns.summary.pageTitle", {
          campaignName: data.name,
        })
      }}
      <template #description>
        {{ $t("campaigns.summary.description") }}
      </template>
    </PageTitle>

    <CampaignFormSummaryCard
      :bpersonName="data.bperson_name ?? ''"
      :productName="data.product_name ?? ''"
      :campaign="data"
      editable
    />

    <template #actions>
      <WizardCardActions>
        <PermissionGuard
          :requires="[{ name: 'CAMPAIGN_SETUP', actions: ['U', 'C'] }]"
        >
          <ButtonGoBack @click="goBack" />
          <ButtonNext @click="handleContinue" :isLoading="isSubmitting">
            {{ $t("campaigns.summary.actionbuttontext") }}
          </ButtonNext>
        </PermissionGuard>

        <PermissionGuard
          :requires="[{ name: 'CAMPAIGN_SETUP', actions: ['R'] }]"
          v-if="!campaignSetupHasUC"
        >
          <div class="tw:flex tw:w-full tw:justify-end">
            <ButtonNext @click="handleRedirect" :isLoading="isSubmitting">
              {{ $t("campaigns.summary.actionbuttontext") }}
            </ButtonNext>
          </div>
        </PermissionGuard>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
