<script setup lang="ts">
import type { SelectOption } from "@/components/forms/base/FieldBaseNewSelect.vue";
import LucaGuideAdsApi, {
  type LucaGuideAd,
  type LucaGuideAdDiagnosisKpiStatus,
  type LucaGuideAdDiagnosisSlot,
  type LucaGuideAdInsightEvidenceKpi,
  type LucaGuideAdInsight,
} from "@/services/guide/LucaGuideAdsApi";
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import type { LucaGuideCampaign } from "@/services/guide/LucaGuideCampaignsApi";
import type { LucaGuideKpi } from "@/services/guide/LucaGuideKpisApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object, ref as yupRef, string } from "yup";

const props = defineProps<{
  ad: LucaGuideAd;
  campaign: Pick<LucaGuideCampaign, "campaign_id" | "name" | "objective_label">;
  accountName: string;
  card: LucaGuideAdDiagnosisSlot;
  // The selected date window, so the slot insight stays consistent with the windowed diagnosis.
  window?: { startDate?: string; endDate?: string };
}>();

const isOpen = defineModel<boolean>({ required: true });
const { t, te } = useI18n();

const schema = computed(() =>
  toTypedSchema(
    object({
      diagnosis: string().trim().required(t("forms.required-field")),
      evidence: string().trim().required(t("forms.required-field")),
      creative_correlation: string().trim().required(t("forms.required-field")),
      objective: string().trim().required(t("forms.required-field")),
      if_clause: string().trim().required(t("forms.required-field")),
      then_clause: string().trim().required(t("forms.required-field")),
      target_kpi: string().required(t("forms.required-field")),
      min: number().required(t("forms.required-field")),
      max: number()
        .required(t("forms.required-field"))
        .moreThan(yupRef("min"), t("forms.max-must-be-greater-than-min")),
      locked_output: string().required(t("forms.required-field")),
      cause_and_effect: string(),
      brief_ready: string().trim().required(t("forms.required-field")),
      recommended_actions: array()
        .of(string().trim().required(t("forms.required-field")))
        .required(),
      selected_recommended_action: number().required(t("forms.required-field")),
      selected_method: string().required(t("forms.required-field")),
      ai_recommended_method: string(),
      risk_of_not_acting: string().trim().required(t("forms.required-field")),
      success_criteria: string().trim().required(t("forms.required-field")),
      // HLG-120: how the linked buyer persona informs this slot (read-only; empty when no context).
      persona_angle: string(),
    }),
  ),
);

const { handleSubmit, isSubmitting, resetForm, values, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {},
  });

const insight = ref<LucaGuideAdInsight | undefined>(undefined);
const kpiOptions = ref<LucaGuideKpi[]>([]);
const isLoading = ref(false);
const isSynthesizing = ref(false);
const canSynthesize = ref(false);
const lastSynthesisKey = ref<string | undefined>();
const isRecommendingMethod = ref(false);
const methodReason = ref<string | undefined>();

const METHOD_ICONS: Record<string, string> = {
  AB_ISOLATION: "tabler:flask",
  ESCALATING_GROUP: "tabler:chart-arrows-vertical",
  CREATIVE_VARIANTS: "tabler:palette",
};

function getSynthesisKey(source: {
  if_clause?: string;
  then_clause?: string;
  target_kpi?: string;
  min?: number;
  max?: number;
}) {
  return [
    source.if_clause?.trim() ?? "",
    source.then_clause?.trim() ?? "",
    source.target_kpi?.trim() ?? "",
    source.min,
    source.max,
  ].join("\0");
}

const title = computed(() => insight.value?.title || props.card?.title || "");

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

const adDiagnosis = computed(() => insight.value?.ad_diagnosis);

const kpiStatusByLabel = computed(() => {
  const statuses = new Map<string, LucaGuideAdDiagnosisKpiStatus>();

  for (const kpi of props.card?.kpis ?? []) {
    statuses.set(kpi.label.trim().toLowerCase(), kpi.status);
  }

  return statuses;
});

function getKpiStatus(
  kpi: LucaGuideAdInsightEvidenceKpi,
): LucaGuideAdDiagnosisKpiStatus | undefined {
  return kpiStatusByLabel.value.get(kpi.label.trim().toLowerCase());
}

async function loadInsight() {
  if (!props.card) {
    return;
  }

  isLoading.value = true;
  canSynthesize.value = false;

  try {
    const [slotInsight, options] = await Promise.all([
      LucaGuideAdsApi.getSlotInsight(
        props.ad.ad_external_id,
        props.card.slot_index,
        props.window,
      ),
      LucaGuideCampaignsApi.getKpiOptions(props.campaign.campaign_id),
    ]);

    insight.value = slotInsight;
    kpiOptions.value = options;

    resetForm({
      values: {
        diagnosis: slotInsight.ad_diagnosis.diagnosis,
        evidence: slotInsight.ad_diagnosis.evidence,
        creative_correlation: slotInsight.ad_diagnosis.creative_correlation,
        objective: slotInsight.context.objective,
        locked_output: slotInsight.context.hypothesis.locked_output,
        if_clause: slotInsight.context.hypothesis.if_clause,
        then_clause: slotInsight.context.hypothesis.then_clause,
        target_kpi: slotInsight.context.target_kpi,
        min: slotInsight.context.min,
        max: slotInsight.context.max,
        cause_and_effect: slotInsight.context.cause_and_effect,
        brief_ready: slotInsight.actions.brief_ready,
        recommended_actions: slotInsight.actions.recommended_actions,
        selected_recommended_action: 0,
        selected_method: undefined,
        ai_recommended_method: undefined,
        risk_of_not_acting: slotInsight.actions.risk_of_not_acting,
        success_criteria: slotInsight.actions.success_criteria.join("\n"),
        persona_angle: slotInsight.actions.persona_angle ?? "",
      },
    });

    lastSynthesisKey.value = getSynthesisKey({
      if_clause: slotInsight.context.hypothesis.if_clause,
      then_clause: slotInsight.context.hypothesis.then_clause,
      target_kpi: slotInsight.context.target_kpi,
      min: slotInsight.context.min,
      max: slotInsight.context.max,
    });

    methodReason.value = undefined;

    await nextTick();
    canSynthesize.value = true;
    void refreshRecommendedMethod(slotInsight.context.hypothesis.locked_output);
  } catch (error) {
    console.error("Failed to load ad slot insight:", error);
    throw error;
  } finally {
    isLoading.value = false;
  }
}

const evidenceKpis = computed(() =>
  (adDiagnosis.value?.evidence_kpis ?? []).map((kpi) => ({
    ...kpi,
    status: getKpiStatus(kpi),
  })),
);

const showLoader = computed(
  () => isLoading.value || (isOpen.value && !adDiagnosis.value),
);

watch(
  isOpen,
  async (open) => {
    if (!open) {
      canSynthesize.value = false;
      return;
    }

    await loadInsight();
  },
  { immediate: true },
);

const kpiSelectOptions = computed(() => {
  const options = kpiOptions.value.map((kpi) => ({
    value: kpi.key,
    label: kpi.name,
  }));

  if (
    values.target_kpi &&
    !options.some((option) => option.value === values.target_kpi)
  ) {
    options.unshift({ value: values.target_kpi, label: values.target_kpi });
  }

  return options;
});

const methodOptions = computed<SelectOption[]>(() =>
  (insight.value?.change_methods ?? []).map((method) => {
    const translationKey = `luca-guide.ads.detail.insight.change_methods.${method.value}`;
    const isAiRecommended = method.value === values.ai_recommended_method;

    return {
      value: method.value,
      label: te(translationKey) ? t(translationKey) : method.label,
      icon: METHOD_ICONS[method.value] ?? "tabler:flask",
      chip: isAiRecommended
        ? {
            label: t("luca-guide.ads.detail.insight.ai-badge"),
            color: "primary",
          }
        : undefined,
    };
  }),
);

const selectedMethodIcon = computed(() => {
  const method = values.selected_method;
  if (!method) {
    return "tabler:flask";
  }
  return METHOD_ICONS[method] ?? "tabler:flask";
});

const isAiRecommendedMethodSelected = computed(
  () =>
    Boolean(values.ai_recommended_method) &&
    values.selected_method === values.ai_recommended_method,
);

const selectedRecommendedAction = computed({
  get: () => values.selected_recommended_action,
  set: (value: number) => setFieldValue("selected_recommended_action", value),
});

async function refreshRecommendedMethod(synthesizedHypothesis: string) {
  const hypothesis = synthesizedHypothesis.trim();
  if (!hypothesis) {
    return;
  }

  isRecommendingMethod.value = true;

  try {
    const response = await LucaGuideAdsApi.recommendHypothesisMethod({
      ad_external_id: props.ad.ad_external_id,
      slot_index: props.card.slot_index,
      synthesized_hypothesis: hypothesis,
    });

    methodReason.value = response.reason;
    setFieldValue("ai_recommended_method", response.ai_recommended_method);
    setFieldValue("selected_method", response.ai_recommended_method);
  } catch (error) {
    console.error("Failed to recommend hypothesis method:", error);
  } finally {
    isRecommendingMethod.value = false;
  }
}

watchDebounced(
  () => ({
    if_clause: values.if_clause,
    then_clause: values.then_clause,
    target_kpi: values.target_kpi,
    min: values.min,
    max: values.max,
  }),
  async (source) => {
    if (!canSynthesize.value) {
      return;
    }

    const if_clause = source.if_clause?.trim();
    const then_clause = source.then_clause?.trim();
    const target_kpi = source.target_kpi?.trim();
    const min = source.min;
    const max = source.max;

    if (!if_clause || !then_clause || !target_kpi) {
      return;
    }

    if (typeof min !== "number" || typeof max !== "number" || min >= max) {
      return;
    }

    const synthesisKey = getSynthesisKey(source);
    if (synthesisKey === lastSynthesisKey.value) {
      return;
    }

    const selectedKpi = kpiOptions.value.find((kpi) => kpi.key === target_kpi);
    const previousSynthesisKey = lastSynthesisKey.value;

    lastSynthesisKey.value = synthesisKey;
    isSynthesizing.value = true;

    try {
      const response = await LucaGuideAdsApi.synthesizeHypothesis({
        if_condition: if_clause,
        then_condition: then_clause,
        kpi_name: selectedKpi?.name ?? target_kpi,
        min_pct: min,
        max_pct: max,
      });

      setFieldValue("locked_output", response.synthesized_hypothesis);
    } catch (error) {
      lastSynthesisKey.value = previousSynthesisKey;
      console.error("Failed to synthesize hypothesis:", error);
      return;
    } finally {
      isSynthesizing.value = false;
    }

    if (values.locked_output) {
      await refreshRecommendedMethod(values.locked_output);
    }
  },
  { debounce: 2000, deep: true },
);

const onSubmit = handleSubmit(async (values) => {
  if (!insight.value) {
    return;
  }

  try {
    const { blob, filename } = await LucaGuideAdsApi.exportSlotInsightPdf(
      props.ad.ad_external_id,
      insight.value.slot_index,
      {
        slot: insight.value.slot,
        slot_index: insight.value.slot_index,
        title: insight.value.title,
        ad_diagnosis: {
          ...insight.value.ad_diagnosis,
          diagnosis: values.diagnosis,
          evidence: values.evidence,
          creative_correlation: values.creative_correlation,
        },
        context: {
          ...insight.value.context,
          objective: values.objective,
          hypothesis: {
            ...insight.value.context.hypothesis,
            if_clause: values.if_clause,
            then_clause: values.then_clause,
            locked_output: values.locked_output,
          },
          target_kpi: values.target_kpi,
          min: values.min,
          max: values.max,
          cause_and_effect:
            values.cause_and_effect ?? insight.value.context.cause_and_effect,
        },
        actions: {
          ...insight.value.actions,
          brief_ready: values.brief_ready,
          recommended_actions: [...values.recommended_actions],
          risk_of_not_acting: values.risk_of_not_acting,
          success_criteria: [values.success_criteria],
        },
      },
    );

    downloadBlob(blob, filename);
  } catch (error) {
    console.error("Failed to export ad slot insight PDF:", error);
    throw error;
  }
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
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      <template #before>
        <p
          class="tw:mb-1 tw:flex tw:items-center tw:gap-1 tw:text-secondary-text"
        >
          <Icon icon="tabler:palette" class="tw:text-base" />

          <span class="tw:text-xs tw:font-semibold tw:uppercase">
            {{ $t("luca-guide.ads.detail.diagnosis.meta-label") }}
          </span>
        </p>
      </template>

      {{ title || "—" }}

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
            <CircleLoaderDefault v-if="showLoader" style="min-height: 200px" />

            <FieldsContainer v-else spacing="md">
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
                  v-for="kpi in evidenceKpis"
                  :key="kpi.label"
                  stacked
                  :label="kpi.label"
                  :value="kpi.value"
                  :benchmark="kpi.benchmark"
                  :status="kpi.status"
                />
              </div>

              <FieldTextarea
                name="creative_correlation"
                :label="
                  $t('luca-guide.ads.detail.insight.creative-correlation-label')
                "
                required
              />
            </FieldsContainer>
          </Accordion>

          <Accordion
            :title="$t('luca-guide.ads.detail.insight.accordion-hypothesis')"
            titleClass="tw:text-base tw:font-semibold"
          >
            <CircleLoaderDefault v-if="showLoader" style="min-height: 200px" />

            <FieldsContainer v-else spacing="md">
              <FieldTextarea
                name="objective"
                :label="$t('luca-guide.ads.detail.insight.objective-label')"
                required
              />

              <FieldsContainer
                spacing="md"
                class="tw:rounded-xl tw:border tw:border-blue-300 tw:bg-[#CCF1F633] tw:p-4"
              >
                <FieldTextarea
                  name="locked_output"
                  :label="
                    $t('luca-guide.ads.detail.insight.if-then-hypothesis')
                  "
                  disabled
                  :loading="isSynthesizing"
                  :rows="3"
                />

                <FieldText
                  name="if_clause"
                  :label="$t('luca-guide.ads.detail.insight.if-label')"
                  required
                >
                  <template #label>
                    <span class="tw:text-blue-500">
                      {{ $t("luca-guide.ads.detail.insight.if-label") }}
                    </span>
                  </template>
                </FieldText>

                <FieldText
                  name="then_clause"
                  :label="$t('luca-guide.ads.detail.insight.then-label')"
                  required
                >
                  <template #label>
                    <span class="tw:text-blue-900">
                      {{ $t("luca-guide.ads.detail.insight.then-label") }}
                    </span>
                  </template>
                </FieldText>

                <div
                  class="tw:grid tw:grid-cols-1 tw:gap-3 tw:sm:grid-cols-[minmax(0,1fr)_110px_110px]"
                >
                  <FieldAutocomplete
                    name="target_kpi"
                    :label="
                      $t('luca-guide.ads.detail.insight.target-kpi-label')
                    "
                    :options="kpiSelectOptions"
                    :placeholder="
                      $t('luca-guide.ads.detail.insight.target-kpi-placeholder')
                    "
                    required
                  />

                  <FieldNumber
                    name="min"
                    :label="
                      $t('luca-guide.ads.detail.insight.min-percent-label')
                    "
                    :digits="0"
                    required
                  />

                  <FieldNumber
                    name="max"
                    :label="
                      $t('luca-guide.ads.detail.insight.max-percent-label')
                    "
                    :digits="0"
                    required
                  />
                </div>
              </FieldsContainer>

              <FieldTextarea
                name="cause_and_effect"
                :label="
                  $t('luca-guide.ads.detail.insight.creative-angle-label')
                "
              />
            </FieldsContainer>
          </Accordion>

          <Accordion
            :title="$t('luca-guide.ads.detail.insight.accordion-actions')"
            titleClass="tw:text-base tw:font-semibold"
          >
            <CircleLoaderDefault v-if="showLoader" style="min-height: 200px" />

            <FieldsContainer v-else spacing="md">
              <FieldTextarea
                name="brief_ready"
                :label="
                  $t('luca-guide.ads.detail.insight.interpretation-label')
                "
                required
              />

              <div
                class="tw:flex tw:flex-col tw:gap-4 tw:rounded-xl tw:border tw:border-blue-300 tw:bg-[#CCF1F633] tw:p-3"
              >
                <div class="tw:flex tw:flex-col tw:gap-8">
                  <div
                    class="tw:flex tw:items-center tw:justify-between tw:gap-3"
                  >
                    <p
                      class="tw:flex tw:items-center tw:gap-1 tw:text-xs tw:font-bold tw:text-blue-900 tw:uppercase"
                    >
                      <Icon icon="tabler:bulb" class="tw:text-base" />
                      <span>
                        {{
                          $t(
                            "luca-guide.ads.detail.insight.recommendation-actions",
                          )
                        }}
                      </span>
                    </p>

                    <span class="tw:text-xs tw:font-medium tw:text-blue-500">
                      {{
                        $t("luca-guide.ads.detail.insight.select-one-option")
                      }}
                    </span>
                  </div>

                  <div
                    v-for="(_, index) in values.recommended_actions"
                    :key="index"
                    class="tw:flex tw:items-center tw:gap-3"
                  >
                    <FieldBaseRadio
                      :name="`selected_recommended_action-${index}`"
                      :value="index"
                      v-model="selectedRecommendedAction"
                    />

                    <FieldEditableText
                      :name="`recommended_actions.${index}`"
                      type="textarea"
                      variant="text"
                      :fit="false"
                      class="tw:grow tw:text-sm tw:font-medium tw:text-blue-900"
                      required
                    />
                  </div>
                </div>

                <hr class="tw:border-blue-200" />

                <FieldNewSelect
                  name="selected_method"
                  :label="
                    $t('luca-guide.ads.detail.insight.change-method-label')
                  "
                  :options="methodOptions"
                  :leftIcon="selectedMethodIcon"
                  :loading="isSynthesizing || isRecommendingMethod"
                  required
                >
                  <template v-if="isAiRecommendedMethodSelected" #right>
                    <Chip
                      size="sm"
                      color="primary"
                      class="tw:whitespace-nowrap"
                    >
                      {{ $t("luca-guide.ads.detail.insight.ai-badge") }}
                    </Chip>
                  </template>

                  <template
                    v-if="isAiRecommendedMethodSelected && methodReason"
                    #hint
                  >
                    {{ methodReason }}
                  </template>
                </FieldNewSelect>
              </div>

              <Alert v-if="values.persona_angle" type="info">
                <template #title>
                  {{ $t("luca-guide.ads.detail.insight.persona-angle") }}
                </template>

                {{ values.persona_angle }}
              </Alert>

              <Alert type="error">
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

      <Button
        type="submit"
        leftIcon="tabler:upload"
        :isLoading="isSubmitting"
        :disabled="showLoader"
      >
        {{ $t("luca-guide.ads.detail.insight.export-to-pdf") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
