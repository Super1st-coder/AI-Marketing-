<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { number, object } from "yup";
import LucaGuideOnboardingApi, {
  type LucaGuideThresholdCategory,
  type LucaGuideThresholdItem,
  type LucaGuideThresholdItemInput,
} from "@/services/guide/LucaGuideOnboardingApi";
import type { ClassificationThresholdKey } from "@/constants/guide/classification-thresholds";

const { t } = useI18n();
const store = useLucaGuideLayoutStore();
const router = useRouter();
const { goBack } = useMultiStepFormContext();

const [savedThresholds, thresholdDefaults] = await Promise.all([
  LucaGuideOnboardingApi.getThresholds(),
  LucaGuideOnboardingApi.getThresholdDefaults(),
]);

function getItemForCategory(
  category: LucaGuideThresholdCategory,
  items: LucaGuideThresholdItem[],
) {
  return items.find((item) => item.category === category);
}

function toFormValues(item: LucaGuideThresholdItem | undefined) {
  if (!item) {
    return undefined;
  }

  return {
    min_impressions: item.min_impressions,
    min_conversions: item.min_conversions,
    min_days_running: item.min_days_running,
    kpi_band_pct: Number(item.kpi_band_pct),
  };
}

function getInitialItem(category: LucaGuideThresholdCategory) {
  return (
    getItemForCategory(category, savedThresholds) ??
    getItemForCategory(category, thresholdDefaults)
  );
}

const createThresholdSchema = () =>
  object({
    min_impressions: number().required(t("forms.required-field")),
    min_conversions: number().required(t("forms.required-field")),
    min_days_running: number().required(t("forms.required-field")),
    kpi_band_pct: number().required(t("forms.required-field")),
  });

const schema = computed(() =>
  toTypedSchema(
    object({
      winner: createThresholdSchema(),
      scalable: createThresholdSchema(),
      promising: createThresholdSchema(),
      losing: createThresholdSchema(),
    }),
  ),
);

const initialValues = {
  winner: toFormValues(getInitialItem("winner")),
  scalable: toFormValues(getInitialItem("scalable")),
  promising: toFormValues(getInitialItem("promising")),
  losing: toFormValues(getInitialItem("losing")),
};

const { handleSubmit, isSubmitting, values, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues,
  });

function resetSection(key: ClassificationThresholdKey) {
  const defaults = toFormValues(getItemForCategory(key, thresholdDefaults));

  if (!defaults) {
    return;
  }

  setFieldValue(`${key}.min_impressions`, defaults.min_impressions);
  setFieldValue(`${key}.min_conversions`, defaults.min_conversions);
  setFieldValue(`${key}.min_days_running`, defaults.min_days_running);
  setFieldValue(`${key}.kpi_band_pct`, defaults.kpi_band_pct);
}

function resetAllSections() {
  for (const { key } of CLASSIFICATION_THRESHOLDS) {
    resetSection(key);
  }
}

function formatThresholdNumber(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) return "—";
  return formatNumberValue(value, DEFAULT_NUMBER_LOCALE);
}

function formatKpiPercent(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) return "—";
  return formatPercentValue(value, DEFAULT_NUMBER_LOCALE);
}

const onSubmit = handleSubmit(async (formValues) => {
  const items: LucaGuideThresholdItemInput[] = CLASSIFICATION_THRESHOLDS.map(
    ({ key }) => {
      const slot = formValues[key];

      return {
        category: key,
        min_impressions: slot.min_impressions,
        min_conversions: slot.min_conversions,
        min_days_running: slot.min_days_running,
        kpi_band_pct: slot.kpi_band_pct,
        use_conversions: slot.min_conversions > 0,
      };
    },
  );

  await LucaGuideOnboardingApi.setThresholds(items);
  const state = await LucaGuideOnboardingApi.complete();

  store.completedOnboardingSteps = 3;
  store.isOnboardingCompleted = state.has_completed;

  router.push({ name: "LucaGuide" });
});
</script>

<template>
  <FormStepLayout as="form" @submit.prevent="onSubmit" :maxWidth="1096">
    <template #stepper>
      <MultiStepFormStepper />
    </template>

    <PageTitle>
      {{ $t("luca-guide.onboarding.classification-thresholds.title") }}
      <template #description>
        {{ $t("luca-guide.onboarding.classification-thresholds.description") }}
      </template>

      <template #after>
        <Button
          type="button"
          variant="outlined"
          color="secondary"
          size="sm"
          leftIcon="tabler:rotate"
          :shadow="false"
          :disabled="isSubmitting"
          class="tw:whitespace-nowrap"
          @click="resetAllSections"
        >
          {{
            $t(
              "luca-guide.onboarding.classification-thresholds.reset-to-defaults",
            )
          }}
        </Button>
      </template>
    </PageTitle>

    <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:lg:grid-cols-2">
      <CardBase
        v-for="section in CLASSIFICATION_THRESHOLDS"
        :key="section.key"
        :color="section.color"
        softBackground
        :borderWidth="2"
        :shadow="false"
        borderRadius="md"
        class="tw:flex tw:flex-col tw:gap-5 tw:p-6"
      >
        <CardTitle :icon="section.icon" :iconVariant="section.iconVariant">
          {{
            $t(
              `luca-guide.onboarding.classification-thresholds.statuses.${section.key}`,
            )
          }}

          <template #subtitle>
            {{
              $t(
                `luca-guide.onboarding.classification-thresholds.subtitles.${section.key}`,
              )
            }}
          </template>

          <template #after>
            <button
              type="button"
              class="tw:flex tw:gap-2 tw:text-sm tw:font-medium tw:text-gray-500"
              :disabled="isSubmitting"
              @click="resetSection(section.key)"
            >
              <Icon icon="tabler:rotate" class="tw:text-[20px]" />

              {{ $t("luca-guide.onboarding.classification-thresholds.reset") }}
            </button>
          </template>
        </CardTitle>

        <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:sm:grid-cols-2">
          <FieldNumber
            :name="`${section.key}.min_impressions`"
            :label="
              $t(
                'luca-guide.onboarding.classification-thresholds.min-impressions',
              )
            "
            :digits="0"
            :disabled="isSubmitting"
          />

          <FieldNumber
            :name="`${section.key}.min_conversions`"
            :label="
              $t(
                'luca-guide.onboarding.classification-thresholds.min-conversions',
              )
            "
            :digits="0"
            :disabled="isSubmitting"
          />

          <FieldNumber
            :name="`${section.key}.min_days_running`"
            :label="
              $t(
                'luca-guide.onboarding.classification-thresholds.min-days-running',
              )
            "
            :digits="0"
            :disabled="isSubmitting"
          />

          <FieldNumber
            :name="`${section.key}.kpi_band_pct`"
            :label="
              section.kpiOperator === 'gt'
                ? $t(
                    'luca-guide.onboarding.classification-thresholds.kpi-gt-target',
                  )
                : $t(
                    'luca-guide.onboarding.classification-thresholds.kpi-lte-target',
                  )
            "
            :digits="2"
            rightIcon="tabler:percentage"
            :disabled="isSubmitting"
          />
        </div>

        <CardBase class="tw:px-4 tw:py-3" borderRadius="sm">
          <i18n-t
            :keypath="
              values[section.key]?.min_conversions
                ? 'luca-guide.onboarding.classification-thresholds.rule'
                : 'luca-guide.onboarding.classification-thresholds.rule-without-conversions'
            "
            tag="p"
            class="tw:text-sm tw:text-secondary-text tw:italic"
          >
            <template #status>
              <strong>{{
                $t(
                  `luca-guide.onboarding.classification-thresholds.statuses.${section.key}`,
                )
              }}</strong>
            </template>

            <template #impressions>
              <strong>
                {{
                  formatThresholdNumber(values[section.key]?.min_impressions)
                }}
              </strong>
            </template>

            <template #conversions>
              <strong>
                {{
                  formatThresholdNumber(values[section.key]?.min_conversions)
                }}
              </strong>
            </template>

            <template #days>
              <strong>
                {{
                  formatThresholdNumber(values[section.key]?.min_days_running)
                }}
              </strong>
            </template>

            <template #kpi>
              <span>CAC</span>
            </template>

            <template #operator>
              <span>{{ section.kpiOperator === "gt" ? ">" : "≤" }}</span>
            </template>

            <template #kpiPercent>
              <strong>
                {{ formatKpiPercent(values[section.key]?.kpi_band_pct) }}
              </strong>
            </template>
          </i18n-t>
        </CardBase>
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
          {{
            $t("luca-guide.onboarding.classification-thresholds.finish-button")
          }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
