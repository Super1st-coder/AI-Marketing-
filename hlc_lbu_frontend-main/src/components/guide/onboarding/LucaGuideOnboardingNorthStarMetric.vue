<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { number, object, string } from "yup";
import LucaGuideKpisApi from "@/services/guide/LucaGuideKpisApi";
import LucaGuideOnboardingApi, {
  LUCA_GUIDE_NORTH_STAR_PRIORITIES,
  type LucaGuideNorthStarItem,
  type LucaGuideNorthStarItemInput,
  type LucaGuideNorthStarPriority,
} from "@/services/guide/LucaGuideOnboardingApi";
import {
  getKpiUnitFromFormatType,
  getLucaGuideKpiStageLabel,
  getLucaGuideKpiStageRank,
} from "@/constants/guide/kpis";

const { t } = useI18n();
const store = useLucaGuideLayoutStore();
const { goBack, goNext } = useMultiStepFormContext();

const [kpis, northStarItems] = await Promise.all([
  LucaGuideKpisApi.list(),
  LucaGuideOnboardingApi.getNorthStar(),
]);

const allKpiOptions = computed(() =>
  [...kpis]
    .sort(
      (a, b) =>
        getLucaGuideKpiStageRank(a.stage) - getLucaGuideKpiStageRank(b.stage),
    )
    .map((kpi) => ({
      value: kpi.key,
      label: t(`luca-guide.kpis.${kpi.key}.long`),
      group: getLucaGuideKpiStageLabel(kpi.stage, t),
    })),
);

function getKpiOptionsFor(priority: LucaGuideNorthStarPriority) {
  const selectedElsewhere = new Set(
    LUCA_GUIDE_NORTH_STAR_PRIORITIES.filter((key) => key !== priority)
      .map((key) => values[key]?.kpi)
      .filter((kpi): kpi is string => Boolean(kpi)),
  );

  return allKpiOptions.value.filter(
    (option) => !selectedElsewhere.has(option.value),
  );
}

function getKpiUnit(kpiKey: string | null | undefined) {
  return getKpiUnitFromFormatType(
    kpis.find((kpi) => kpi.key === kpiKey)?.format_type,
  );
}

function getSlotFromItems(
  items: LucaGuideNorthStarItem[],
  priority: LucaGuideNorthStarPriority,
) {
  const item = items.find((entry) => entry.priority === priority);
  if (!item) {
    return undefined;
  }

  const kpi = kpis.find((entry) => entry.id === item.kpi_id);
  if (!kpi) {
    return undefined;
  }

  return {
    kpi: kpi.key,
    targetValue: Number(item.target_value),
  };
}

const initialValues = {
  primary: getSlotFromItems(northStarItems, "primary"),
  secondary: getSlotFromItems(northStarItems, "secondary"),
  tertiary: getSlotFromItems(northStarItems, "tertiary"),
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

const { handleSubmit, isSubmitting, values } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues,
});

const onSubmit = handleSubmit(async (formValues) => {
  const items: LucaGuideNorthStarItemInput[] = [];

  for (const priority of LUCA_GUIDE_NORTH_STAR_PRIORITIES) {
    const slot = formValues[priority];
    if (!slot?.kpi || slot.targetValue === undefined) {
      continue;
    }

    const kpi = kpis.find((entry) => entry.key === slot.kpi);
    if (!kpi) {
      continue;
    }

    items.push({
      priority,
      kpi_id: kpi.id,
      target_value: slot.targetValue,
    });
  }

  await LucaGuideOnboardingApi.setNorthStar(items);

  store.completedOnboardingSteps = Math.max(store.completedOnboardingSteps, 3);

  goNext();
});

const kpiSections = [
  {
    key: "primary",
    titleKey: "luca-guide.north-star-kpi-priorities.primary-kpi",
    required: true,
    highlighted: true,
  },
  {
    key: "secondary",
    titleKey: "luca-guide.north-star-kpi-priorities.secondary-kpi",
    required: false,
    highlighted: false,
  },
  {
    key: "tertiary",
    titleKey: "luca-guide.north-star-kpi-priorities.tertiary-kpi",
    required: false,
    highlighted: false,
  },
] as const;
</script>

<template>
  <FormStepLayout as="form" @submit.prevent="onSubmit" :maxWidth="1096">
    <template #stepper>
      <MultiStepFormStepper />
    </template>

    <PageTitle>
      {{ $t("luca-guide.onboarding.north-star-metric.title") }}
      <template #description>
        {{ $t("luca-guide.onboarding.north-star-metric.description") }}
      </template>
    </PageTitle>

    <Alert type="info">
      <template #title>
        {{ $t("luca-guide.onboarding.north-star-metric.alert-title") }}
      </template>

      Most accounts run <strong>several products</strong> with different
      acquisition costs and prices — so a single account-wide
      <strong>CAC</strong> or <strong>ROAS</strong> rarely makes sense here.
      Prefer portfolio-level health metrics like
      <strong>CPM / reach (visibility), frequency or CPC</strong>. You'll still
      set the right <strong>CAC / ROAS</strong> target
      <strong>per campaign</strong> later — that's where product economics
      belong. These account KPIs only power the overview on the
      <strong>Campaigns</strong> page.
    </Alert>

    <div class="tw:flex tw:flex-col tw:gap-4">
      <CardBase
        v-for="section in kpiSections"
        :key="section.key"
        :outlineColor="section.highlighted ? 'primary' : 'default'"
        :borderWidth="2"
        :shadow="false"
        borderRadius="md"
        class="tw:flex tw:flex-col tw:gap-5 tw:p-6"
      >
        <h2 class="tw:text-xl tw:font-bold">
          {{ $t(section.titleKey) }}<span v-if="section.required">*</span>
        </h2>

        <div
          class="tw:flex tw:flex-col tw:gap-5 tw:lg:flex-row tw:lg:items-start"
        >
          <FieldAutocomplete
            :name="`${section.key}.kpi`"
            :label="$t('luca-guide.onboarding.north-star-metric.kpi')"
            :placeholder="
              $t('luca-guide.onboarding.north-star-metric.search-placeholder')
            "
            :options="getKpiOptionsFor(section.key)"
            leftIcon="tabler:search"
            class="tw:lg:grow"
            clearable
            :disabled="isSubmitting"
          />

          <FieldNumber
            :name="`${section.key}.targetValue`"
            :label="$t('luca-guide.onboarding.north-star-metric.target-value')"
            class="tw:lg:shrink-0 tw:lg:basis-[300px]"
            :disabled="isSubmitting"
            :leftIcon="getKpiUnit(values[section.key]?.kpi)?.leftIcon"
            :rightIcon="getKpiUnit(values[section.key]?.kpi)?.rightIcon"
          />
        </div>
      </CardBase>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <Button
          type="submit"
          icon="tabler-arrow-right"
          :isLoading="isSubmitting"
        >
          {{ $t("global.continue") }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
