<script setup lang="ts">
import type { LucaGuideAd } from "@/services/guide/LucaGuideAdsApi";
import type { LucaGuideCampaign } from "@/services/guide/LucaGuideCampaignsApi";
import type { LucaGuideAdRecommendedNextMoveCardData } from "./LucaGuideAdRecommendedNextMoveCard.vue";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const props = defineProps<{
  ad: LucaGuideAd;
  campaign: Pick<LucaGuideCampaign, "campaign_id" | "name" | "objective_label">;
  accountName: string;
  card: LucaGuideAdRecommendedNextMoveCardData;
}>();

const isOpen = defineModel<boolean>({ required: true });
const { t } = useI18n();

const schema = computed(() =>
  toTypedSchema(
    object({
      title: string().trim().required(t("forms.required-field")),
      diagnosis: string().trim().required(t("forms.required-field")),
      evidence: string().trim().required(t("forms.required-field")),
      interpretation: string().trim().required(t("forms.required-field")),
      recommendation: string().trim().required(t("forms.required-field")),
      risk_of_not_acting: string().trim().required(t("forms.required-field")),
      success_criteria: string().trim().required(t("forms.required-field")),
    }),
  ),
);

const { values } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    title: props.card.title,
    diagnosis: props.card.diagnosis,
    evidence: props.card.evidence,
    interpretation: props.card.description,
    recommendation: props.card.recommendation,
    risk_of_not_acting: props.card.riskOfNotActing,
    success_criteria: props.card.successCriteria,
  },
});

const contextLabel = computed(() => {
  const context = [
    props.ad.ad_name,
    props.campaign.name,
    props.campaign.objective_label,
  ].join(" · ");

  if (!context) {
    return undefined;
  }

  return t("luca-guide.ads.detail.insight.ad-context", { context });
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="1080"
    closeButton
    scrollable="inner"
    as="form"
    v-slot="{ close }"
    alignment="top"
    @submit.prevent
  >
    <ModalHeader>
      <template #before>
        <p
          class="tw:mb-1 tw:flex tw:items-center tw:gap-1 tw:text-secondary-text"
        >
          <Icon :icon="card.icon" class="tw:text-base" />

          <span class="tw:text-xs tw:font-semibold tw:uppercase">
            {{ card.category }}
          </span>
        </p>

        <FieldEditableText
          name="title"
          type="text"
          variant="text"
          class="tw:mr-12 tw:text-2xl tw:font-bold"
          :class="{ 'tw:mb-2': contextLabel }"
        />
      </template>

      <template v-if="contextLabel" #description>
        {{ contextLabel }}
      </template>
    </ModalHeader>

    <ModalBody>
      <div
        class="tw:grid tw:grid-cols-1 tw:items-start tw:gap-6 tw:lg:grid-cols-[1fr_337px]"
      >
        <aside
          class="tw:flex tw:flex-col tw:gap-3 tw:lg:sticky tw:lg:top-0 tw:lg:order-last"
        >
          <p
            class="tw:text-xs tw:font-semibold tw:text-secondary-text tw:uppercase"
          >
            {{ $t("luca-guide.ads.detail.insight.briefing-label") }}
          </p>

          <Suspense v-if="isOpen">
            <LucaGuideAdPreviewPanel
              :ad="ad"
              :accountName="accountName"
              size="sm"
              clampLines
            />

            <template #fallback>
              <CircleLoaderDefault style="min-height: 200px" />
            </template>
          </Suspense>
        </aside>

        <AccordionList variant="card">
          <Accordion
            openByDefault
            :title="$t('luca-guide.ads.detail.diagnosis.section-title')"
            titleClass="tw:text-base tw:font-semibold"
          >
            <FieldsContainer spacing="md">
              <FieldTextarea
                name="diagnosis"
                :label="$t('luca-guide.ads.detail.insight.diagnosis-label')"
                required
              />

              <FieldTextarea
                name="evidence"
                :label="$t('luca-guide.ads.detail.insight.evidence-label')"
                required
              />

              <div class="tw:grid tw:grid-cols-1 tw:gap-3 tw:sm:grid-cols-3">
                <LucaGuideAdKpiCard
                  v-for="kpi in card.kpis"
                  :key="kpi.label"
                  stacked
                  :label="kpi.label"
                  :value="kpi.value"
                  :benchmark="kpi.benchmark"
                  :status="kpi.status"
                />
              </div>
            </FieldsContainer>
          </Accordion>

          <Accordion
            :title="$t('luca-guide.ads.detail.insight.accordion-actions')"
            titleClass="tw:text-base tw:font-semibold"
          >
            <FieldsContainer spacing="md">
              <FieldTextarea
                name="interpretation"
                :label="
                  $t('luca-guide.ads.detail.insight.interpretation-label')
                "
                required
              />

              <CardBase
                v-if="values.recommendation"
                :shadow="false"
                :color="card.tone"
                :outlineColor="card.tone"
                softBackground
                class="tw:p-3"
                borderRadius="sm"
              >
                <Chip
                  v-if="card.actionLabel"
                  size="sm"
                  :color="card.tone"
                  variant="label"
                  uppercase
                  class="tw:mb-2"
                >
                  {{ card.actionLabel }}
                </Chip>

                <p
                  class="tw:text-xs tw:font-medium"
                  :class="{
                    'tw:text-primary-800': card.tone === 'primary',
                    'tw:text-success-800': card.tone === 'success',
                    'tw:text-warning-900': card.tone === 'warning',
                    'tw:text-blue-900': card.tone === 'info',
                  }"
                >
                  {{ values.recommendation }}
                </p>
              </CardBase>

              <Alert v-if="values.risk_of_not_acting" type="error">
                <template #title>
                  {{ $t("luca-guide.ads.detail.insight.risk-of-not-acting") }}
                </template>

                {{ values.risk_of_not_acting }}
              </Alert>

              <FieldTextarea
                name="success_criteria"
                :label="
                  $t('luca-guide.ads.detail.insight.success-criteria-label')
                "
                required
              />
            </FieldsContainer>
          </Accordion>
        </AccordionList>
      </div>
    </ModalBody>

    <ModalFooter>
      <template #before>
        <Button
          type="button"
          color="secondary"
          variant="outlined"
          @click="close"
        >
          {{ $t("global.cancel") }}
        </Button>
      </template>

      <Button type="button" leftIcon="tabler:clipboard-plus">
        {{ $t("luca-guide.ads.detail.diagnosis.add-to-plan") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
