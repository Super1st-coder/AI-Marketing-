<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { number, object } from "yup";
import { computed, watch } from "vue";

const props = defineProps<{
  creativeId: number;
  // The summary shows the checks without allowing changes
  readonly?: boolean;
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

// Get creative data
const creative = computed(() =>
  preCheckStore.creativesWithData.find((c) => c.idx === props.creativeId)!,
);

const minimumBudget = computed(() => {
  return creative.value?.min_daily_budget ?? 0;
});

// Error message from API
const generalErrorMessage = ref<string | undefined>(undefined);

// Schema
const schema = computed(() =>
  toTypedSchema(
    object({
      daily_budget: number()
        .required(t("forms.required-field"))
        .min(
          minimumBudget.value,
          t("forms.min-value", {
            min: minimumBudget.value.toFixed(2),
          }),
        )
        .typeError(t("forms.must-be-number")),
    }),
  ),
);

const { handleSubmit, meta, values, isSubmitting, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      daily_budget: preCheckStore.getMinimumBudget(props.creativeId),
    },
  });

// Clear API error when user changes the form value
watch(
  () => values.daily_budget,
  () => {
    if (generalErrorMessage.value) {
      generalErrorMessage.value = undefined;
    }
  },
);

const onSubmit = handleSubmit(async (values) => {
  if (props.readonly) {
    return;
  }

  try {
    await preCheckStore.setMinimumBudget(props.creativeId, values.daily_budget);

    isOpen.value = false;
  } catch (error: any) {
    const errorCode = error?.message?.code;

    if (errorCode === "DAT001") {
      // Check for DAT001 error - Minimum budget not found for account currency
      generalErrorMessage.value = t(
        "funnel-flow.paid-social.launchpad.budget-modal.errors.minimum-budget-not-found",
      );
    } else {
      throw error;
    }
  }
});

const handleCancel = () => {
  isOpen.value = false;
};

const handleSetToMinimum = () => {
  setFieldValue("daily_budget", minimumBudget.value);
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="700"
    closeButton
    useCustomClose
    @customClose="handleCancel"
    alignment="top"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.launchpad.budget-modal.title") }}

      <template #description>
        {{ $t("funnel-flow.paid-social.launchpad.budget-modal.description") }}
      </template>

      <template #after>
        <Alert v-if="generalErrorMessage" type="error" class="tw:mt-6">
          <strong>
            {{
              $t("funnel-flow.paid-social.launchpad.budget-modal.error-prefix")
            }}
          </strong>
          {{ generalErrorMessage }}
        </Alert>
        <Alert
          v-else
          :type="meta.valid ? 'success' : 'warning'"
          class="tw:mt-6"
        >
          <template v-if="meta.valid">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.budget-modal.validation.passed",
              )
            }}
          </template>
          <template v-else>
            <strong>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.budget-modal.validation.action-required-prefix",
                )
              }}
            </strong>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.budget-modal.validation.action-required-message",
                { min: minimumBudget.toFixed(2) },
              )
            }}
          </template>

          <template #actions>
            <Link
              v-if="!meta.valid && !readonly"
              is="button"
              underline
              @click="handleSetToMinimum"
            >
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.budget-modal.actions.set-to-minimum",
                )
              }}
            </Link>
          </template>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldMoney
        name="daily_budget"
        :disabled="readonly"
        :label="
          $t(
            'funnel-flow.paid-social.launchpad.budget-modal.fields.daily-budget',
          )
        "
        :currency="
          preCheckStore.preCheckResponse?.data.account_config?.currency
        "
        appendCodeToLabel
        useCurrencyIcon
      >
        <template #hint>
          {{
            $t(
              "funnel-flow.paid-social.launchpad.budget-modal.fields.daily-budget-hint",
            )
          }}
        </template>
      </FieldMoney>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        @click="handleCancel"
      >
        {{ $t("global.close") }}
      </Button>

      <Button
        v-if="!readonly"
        type="submit"
        :disabled="!meta.valid"
        :isLoading="isSubmitting"
      >
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
