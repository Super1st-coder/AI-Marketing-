<script setup lang="ts">
import type { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import {
  getKpiUnitFromFormatType,
  getLucaGuideKpiStageLabel,
  getLucaGuideKpiStageRank,
} from "@/constants/guide/kpis";
import LucaGuideCampaignsApi, {
  type LucaGuideCampaignKpiItem,
} from "@/services/guide/LucaGuideCampaignsApi";
import type { LucaGuideKpi } from "@/services/guide/LucaGuideKpisApi";
import {
  LUCA_GUIDE_NORTH_STAR_PRIORITIES,
  type LucaGuideNorthStarPriority,
} from "@/services/guide/LucaGuideOnboardingApi";
import { CampaignNotFoundError } from "@/services/common-errors";
import { toTypedSchema } from "@vee-validate/yup";
import { number, object, string } from "yup";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const { goBack } = useMultiStepFormContext();

const campaignId = String(route.params.campaignId);

const [kpiOptions, initialCampaignKpis, campaigns] = await Promise.all([
  LucaGuideCampaignsApi.getKpiOptions(campaignId),
  LucaGuideCampaignsApi.getKpis(campaignId),
  LucaGuideCampaignsApi.list(),
]);

const campaign = campaigns.find((item) => item.campaign_id === campaignId);

if (!campaign) {
  throw new CampaignNotFoundError();
}

const kpisById = computed(() => {
  const map = new Map<string, LucaGuideKpi>();
  for (const kpi of kpiOptions) {
    map.set(kpi.id, kpi);
  }
  return map;
});

/** Sort rank for KPI compatibility: lower = higher in the autocomplete list. */
const COMPATIBILITY_ORDER: Record<string, number> = {
  ideal: 0,
  compatible: 1,
  warning: 2,
};

/** Sort rank for KPI alignment: lower = higher in the autocomplete list. */
function getCompatibilityRank(compatibility: string | null | undefined) {
  if (!compatibility) return 3;
  return COMPATIBILITY_ORDER[compatibility] ?? 3;
}

function getKpiAlignmentIcon(compatibility: string | null | undefined) {
  if (compatibility === "ideal") {
    return "tabler:circle-check-filled";
  }
  if (compatibility === "warning") {
    return "tabler:alert-triangle-filled";
  }
  return undefined;
}

function getKpiAlignmentIconClass(compatibility: string | null | undefined) {
  if (compatibility === "ideal") {
    return "tw:text-success";
  }
  if (compatibility === "warning") {
    return "tw:text-warning";
  }
  return undefined;
}

function getSlotFromItems(priority: LucaGuideNorthStarPriority) {
  const item = initialCampaignKpis.items.find(
    (entry) => entry.priority === priority,
  );
  if (!item || !kpisById.value.has(item.kpi_id)) {
    return undefined;
  }

  return {
    kpi: item.kpi_id,
    targetValue: Number(item.target_value),
  };
}

const initialValues = {
  primary: getSlotFromItems("primary"),
  secondary: getSlotFromItems("secondary"),
  tertiary: getSlotFromItems("tertiary"),
};

const mandatoryKpiSchema = computed(() =>
  object({
    kpi: string().required(t("forms.required-field")),
    targetValue: number().required(t("forms.required-field")),
  }),
);

const optionalKpiSchema = computed(() =>
  object({
    kpi: string(),
    targetValue: number().when("kpi", {
      is: (kpi: string | undefined) => Boolean(kpi),
      then: (schema) => schema.required(t("forms.required-field")),
    }),
  }),
);

const schema = computed(() =>
  toTypedSchema(
    object({
      primary: mandatoryKpiSchema.value,
      secondary: optionalKpiSchema.value,
      tertiary: optionalKpiSchema.value,
    }),
  ),
);

const { handleSubmit, isSubmitting, values, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues,
  });

function getKpiOptionsFor(
  priority: LucaGuideNorthStarPriority,
): AutocompleteOption[] {
  const selectedElsewhere = new Set(
    LUCA_GUIDE_NORTH_STAR_PRIORITIES.filter((key) => key !== priority)
      .map((key) => values[key]?.kpi)
      .filter((kpi): kpi is string => Boolean(kpi)),
  );

  return [...kpiOptions]
    .filter((kpi) => !selectedElsewhere.has(kpi.id))
    .sort((a, b) => {
      const stageDiff =
        getLucaGuideKpiStageRank(a.stage) - getLucaGuideKpiStageRank(b.stage);
      if (stageDiff !== 0) {
        return stageDiff;
      }

      return (
        getCompatibilityRank(a.compatibility) -
        getCompatibilityRank(b.compatibility)
      );
    })
    .map((kpi) => ({
      value: kpi.id,
      label: t(`luca-guide.kpis.${kpi.key}.long`),
      group: getLucaGuideKpiStageLabel(kpi.stage, t),
      icon: getKpiAlignmentIcon(kpi.compatibility),
      iconClass: getKpiAlignmentIconClass(kpi.compatibility),
    }));
}

function getSelectedKpi(priority: LucaGuideNorthStarPriority) {
  const id = values[priority]?.kpi;
  if (!id) return undefined;
  return kpisById.value.get(id);
}

function getFieldLeftIcon(priority: LucaGuideNorthStarPriority) {
  const compatibility = getSelectedKpi(priority)?.compatibility;
  return getKpiAlignmentIcon(compatibility) ?? "tabler:search";
}

function getFieldLeftIconClass(priority: LucaGuideNorthStarPriority) {
  return getKpiAlignmentIconClass(getSelectedKpi(priority)?.compatibility);
}

function getKpiUnit(priority: LucaGuideNorthStarPriority) {
  return getKpiUnitFromFormatType(getSelectedKpi(priority)?.format_type);
}

function getWarningMessage(priority: LucaGuideNorthStarPriority) {
  const kpi = getSelectedKpi(priority);
  if (!kpi || kpi.compatibility !== "warning") {
    return undefined;
  }
  return kpi.warning || undefined;
}

// Reset target value when kpi is changed
watch(
  () =>
    LUCA_GUIDE_NORTH_STAR_PRIORITIES.map(
      (priority) => [priority, values[priority]?.kpi] as const,
    ),
  (slots) => {
    for (const [priority, kpi] of slots) {
      if (!kpi) {
        setFieldValue(`${priority}.targetValue`, undefined, false);
      }
    }
  },
);

const onSubmit = handleSubmit(async (formValues) => {
  const items: LucaGuideCampaignKpiItem[] = [];

  for (const priority of LUCA_GUIDE_NORTH_STAR_PRIORITIES) {
    const slot = formValues[priority];
    if (!slot?.kpi || slot.targetValue === undefined) {
      continue;
    }

    if (!kpisById.value.has(slot.kpi)) {
      continue;
    }

    items.push({
      priority,
      kpi_id: slot.kpi,
      target_value: slot.targetValue,
    });
  }

  await LucaGuideCampaignsApi.setKpis(campaignId, items);

  await router.push({
    name: "LucaGuideCampaign",
    params: {
      brandId: route.params.brandId,
      campaignId,
    },
  });
});

const kpiFields = [
  {
    key: "primary" as const,
    titleKey: "luca-guide.north-star-kpi-priorities.primary-kpi",
    required: true,
  },
  {
    key: "secondary" as const,
    titleKey: "luca-guide.north-star-kpi-priorities.secondary-kpi",
    required: false,
  },
  {
    key: "tertiary" as const,
    titleKey: "luca-guide.north-star-kpi-priorities.tertiary-kpi",
    required: false,
  },
];
</script>

<template>
  <FormStepLayout as="form" :maxWidth="1096" @submit.prevent="onSubmit">
    <template #stepper>
      <MultiStepFormStepper />
    </template>

    <PageTitle>
      {{ $t("luca-guide.campaigns.onboarding.metrics-north-star.title") }}
      <template #description>
        {{
          $t("luca-guide.campaigns.onboarding.metrics-north-star.description")
        }}
      </template>

      <!-- TODO: add View Campaign Team button -->
    </PageTitle>

    <LucaGuideCampaignOnboardingMetricsHeader :campaign="campaign" />

    <LucaGuideCampaignOnboardingMetricsBrief />

    <!-- North Star card -->
    <CardBase borderRadius="md" class="tw:flex tw:flex-col tw:gap-6 tw:p-6">
      <div>
        <h2
          class="tw:mb-2 tw:flex tw:items-center tw:gap-1 tw:text-xl tw:font-bold"
        >
          <Icon icon="custom:north-star" class="tw:text-2xl tw:text-primary" />

          <span>
            {{
              $t(
                "luca-guide.campaigns.onboarding.metrics-north-star.card-title",
              )
            }}
          </span>
        </h2>

        <i18n-t
          keypath="luca-guide.campaigns.onboarding.metrics-north-star.card-description"
          tag="p"
          class="tw:text-sm tw:whitespace-pre-line tw:text-secondary-text"
        >
          <template #aligned>
            <Icon
              icon="tabler:circle-check-filled"
              class="tw:inline tw:align-text-bottom tw:text-base tw:text-success"
            />
          </template>
          <template #warning>
            <Icon
              icon="tabler:alert-triangle-filled"
              class="tw:inline tw:align-text-bottom tw:text-base tw:text-warning"
            />
          </template>
        </i18n-t>
      </div>

      <!-- KPIs fields -->
      <FieldBaseControl
        v-for="field in kpiFields"
        :key="field.key"
        :name="`${field.key}.kpi`"
        :label="$t(field.titleKey)"
        :required="field.required"
        orientation="horizontal"
        labelClass="tw:lg:w-[160px] tw:lg:shrink-0"
      >
        <div
          class="tw:flex tw:flex-col tw:gap-4 tw:lg:flex-row tw:lg:items-start"
        >
          <FieldAutocomplete
            :name="`${field.key}.kpi`"
            :placeholder="
              $t(
                'luca-guide.campaigns.onboarding.metrics-north-star.search-placeholder',
              )
            "
            :options="getKpiOptionsFor(field.key)"
            clearable
            :disabled="isSubmitting"
            hideLayout
            class="tw:grow"
            :leftIcon="getFieldLeftIcon(field.key)"
            :leftIconClass="getFieldLeftIconClass(field.key)"
          />

          <FieldNumber
            :key="`${field.key}-target-${values[field.key]?.kpi ?? 'none'}`"
            :name="`${field.key}.targetValue`"
            hideLayout
            selectOnFocus
            class="tw:lg:w-[140px] tw:lg:shrink-0"
            :disabled="isSubmitting || !values[field.key]?.kpi"
            :leftIcon="getKpiUnit(field.key)?.leftIcon"
            :rightIcon="getKpiUnit(field.key)?.rightIcon"
          />
        </div>

        <template v-if="getWarningMessage(field.key)" #after>
          <p
            class="tw:mt-2 tw:flex tw:items-center tw:gap-1 tw:text-sm tw:text-warning"
          >
            <Icon
              icon="tabler:alert-triangle-filled"
              class="tw:shrink-0 tw:text-base"
            />

            <span>{{ getWarningMessage(field.key) }}</span>
          </p>
        </template>
      </FieldBaseControl>
    </CardBase>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <Button type="submit" :isLoading="isSubmitting">
          {{ $t("global.save") }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
