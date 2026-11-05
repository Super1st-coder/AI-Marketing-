<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { UnidentifiedError } from "@/services/common-errors";
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignSummaryAttributes,
} from "@/services/projects/UmbrellaCampaignsApi";

const { t } = useI18n();
const router = useRouter();
const { targetCampaignRoute } = useCampaignQueryShorcut();

const brandId = useBrandId();
const projectId = useProjectId();

const { goBack, data } = useMultiStepFormContext<UmbrellaCampaignFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      story_hero: string().required(t("forms.required-field")).trim(),
      target_customer: string().required(t("forms.required-field")).trim(),
      who_reaching: string().required(t("forms.required-field")).trim(),

      big_idea: string().required(t("forms.required-field")).trim(),
      message: string().required(t("forms.required-field")).trim(),
      hook: string().required(t("forms.required-field")).trim(),

      product_role: string().required(t("forms.required-field")).trim(),
      how_product_shines: string().required(t("forms.required-field")).trim(),
      solution: string().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  keepValuesOnUnmount: true,
  validationSchema: schema,
  initialValues: {
    story_hero:
      data.value.summary_saved?.the_persona.find(
        (item) => item.id === "hero_story",
      )?.content ??
      data.value.summary_generated?.the_persona.find(
        (item) => item.id === "hero_story",
      )?.content,
    target_customer:
      data.value.summary_saved?.the_persona.find(
        (item) => item.id === "customer_reality",
      )?.content ??
      data.value.summary_generated?.the_persona.find(
        (item) => item.id === "customer_reality",
      )?.content,
    who_reaching:
      data.value.summary_saved?.the_persona.find(
        (item) => item.id === "emotional_conflict",
      )?.content ??
      data.value.summary_generated?.the_persona.find(
        (item) => item.id === "emotional_conflict",
      )?.content,

    big_idea:
      data.value.summary_saved?.the_creative_concept.find(
        (item) => item.id === "big_idea",
      )?.content ??
      data.value.summary_generated?.the_creative_concept.find(
        (item) => item.id === "big_idea",
      )?.content,
    message:
      data.value.summary_saved?.the_creative_concept.find(
        (item) => item.id === "core_message",
      )?.content ??
      data.value.summary_generated?.the_creative_concept.find(
        (item) => item.id === "core_message",
      )?.content,
    hook:
      data.value.summary_saved?.the_creative_concept.find(
        (item) => item.id === "hook",
      )?.content ??
      data.value.summary_generated?.the_creative_concept.find(
        (item) => item.id === "hook",
      )?.content,

    product_role:
      data.value.summary_saved?.the_product.find(
        (item) => item.id === "concept_reality_resonance",
      )?.content ??
      data.value.summary_generated?.the_product.find(
        (item) => item.id === "concept_reality_resonance",
      )?.content,
    how_product_shines:
      data.value.summary_saved?.the_product.find(
        (item) => item.id === "customer_journey",
      )?.content ??
      data.value.summary_generated?.the_product.find(
        (item) => item.id === "customer_journey",
      )?.content,
    solution:
      data.value.summary_saved?.the_product.find(
        (item) => item.id === "solution",
      )?.content ??
      data.value.summary_generated?.the_product.find(
        (item) => item.id === "solution",
      )?.content,
  },
});

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  if (!data.value.summary_generated) {
    throw new UnidentifiedError();
  }

  const savedSummary: UmbrellaCampaignSummaryAttributes = {
    the_persona: [
      {
        id: "hero_story",
        title: t("umbrella-campaign.step-summary.hero-title"),
        content: values.story_hero,
      },
      {
        id: "customer_reality",
        title: t("umbrella-campaign.step-summary.customer-reality-title"),
        content: values.target_customer,
      },
      {
        id: "emotional_conflict",
        title: t("umbrella-campaign.step-summary.emotional-conflict-title"),
        content: values.who_reaching,
      },
    ],
    the_creative_concept: [
      {
        id: "big_idea",
        title: t("umbrella-campaign.step-summary.big-idea-title"),
        content: values.big_idea,
      },
      {
        id: "core_message",
        title: t("umbrella-campaign.step-summary.core-message-title"),
        content: values.message,
      },
      {
        id: "hook",
        title: t("umbrella-campaign.step-summary.hook-title"),
        content: values.hook,
      },
    ],
    the_product: [
      {
        id: "concept_reality_resonance",
        title: t("umbrella-campaign.step-summary.product-role-title"),
        content: values.product_role,
      },
      {
        id: "customer_journey",
        title: t("umbrella-campaign.step-summary.how-product-shines-title"),
        content: values.how_product_shines,
      },
      {
        id: "solution",
        title: t("umbrella-campaign.step-summary.solution-title"),
        content: values.solution,
      },
    ],
  };

  await UmbrellaCampaignsApi.saveSummary(brandId, projectId, data.value.id, {
    summary_generated: data.value.summary_generated,
    summary_saved: savedSummary,
  });

  // Navigate to the creative concept list
  disableSaveAlert.value = true;

  if (targetCampaignRoute.value) {
    // Navigate to the campaign
    router.replace(targetCampaignRoute.value);
  } else {
    // Navigate to the creative concept list
    router.push({ name: "UmbrellaCampaignList" });
  }
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=CSPsm6Zm2JU"
    >
      {{
        t("umbrella-campaign.step-summary.title", {
          campaign: data.name,
        })
      }}

      <template #description>
        {{ t("umbrella-campaign.step-summary.description") }}
      </template>
    </PageTitle>

    <UmbrellaCampaignFormSummaryCards :umbrellaCampaign="data" editable />

    <template #actions>
      <WizardCardActions>
        <PermissionGuard
          :requires="[{ name: 'UMBRELLA_CAMPAIGN', actions: ['U'] }]"
        >
          <ButtonGoBack @click="goBack" />
          <ButtonNext :disabled="isSubmitting">
            {{ t("global.save") }}
          </ButtonNext>
        </PermissionGuard>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
