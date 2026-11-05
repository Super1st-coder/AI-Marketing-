<script setup lang="ts">
const props = defineProps<{
  creativeId: number;
  // The summary shows the checks without allowing changes
  readonly?: boolean;
}>();

const isOpen = defineModel<boolean>({ required: true });
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

const initialCreative = computed(() =>
  preCheckStore.getInitialCreative(props.creativeId)!,
);

const maximumSelectable = computed(
  () => initialCreative.value.call_to_action_types_max_amount,
);

// Invalid CTAs from the initial precheck
const invalidCTAs = computed(() =>
  initialCreative.value.call_to_action_types
    .filter((cta) => !cta.valid)
    .map((cta, index) => ({
      id: `invalid-${index}`,
      value: cta.value,
      label: cta.value.replace(/_/g, " "),
      valid: false,
    })),
);

// Get invalid CTA values for validation
const invalidCtaValues = computed(() =>
  invalidCTAs.value.map((cta) => cta.value),
);

// Valid CTAs from the initial precheck
const initialValidCTAs = computed(() =>
  initialCreative.value.call_to_action_types.filter((cta) => cta.valid),
);

// Valid CTAs from the API response
const validCtasFromApi = computed(() => {
  return preCheckStore.preCheckResponse?.data?.valid_ctas ?? [];
});

// Get initial valid CTA values to avoid duplicates
const initialValidCtaValues = computed(() =>
  initialValidCTAs.value.map((cta) => cta.value),
);

// Combined valid CTAs: initial valid + valid_ctas (excluding duplicates)
const validCTAs = computed(() => {
  // Start with initial valid CTAs
  const combined = [...initialValidCTAs.value.map((cta) => cta.value)];

  // Add valid CTAs from API that aren't already in initial valid CTAs
  validCtasFromApi.value.forEach((ctaValue) => {
    if (!initialValidCtaValues.value.includes(ctaValue)) {
      combined.push(ctaValue);
    }
  });

  return combined.map((ctaValue, index) => ({
    id: `valid-${index}`,
    value: ctaValue,
    label: ctaValue.replace(/_/g, " "),
  }));
});

// Initialize with selected CTAs from the store
const selectedCtaValues = ref<string[]>([
  ...preCheckStore.getSelectedCTAs(props.creativeId),
]);

const selectedTotal = computed(() => selectedCtaValues.value.length);

const excessCount = computed(() => {
  return Math.max(0, selectedTotal.value - maximumSelectable.value);
});

const isValidationPassed = computed(() => {
  return (
    selectedTotal.value >= 1 &&
    selectedTotal.value <= maximumSelectable.value &&
    !selectedCtaValues.value.some((ctaValue) =>
      invalidCtaValues.value.includes(ctaValue),
    )
  );
});

const isSaving = ref(false);

function toggleCta(ctaValue: string) {
  const index = selectedCtaValues.value.indexOf(ctaValue);
  if (index > -1) {
    selectedCtaValues.value.splice(index, 1);
  } else {
    // Only add if under limit
    if (selectedTotal.value < maximumSelectable.value) {
      selectedCtaValues.value.push(ctaValue);
    }
  }
}

function isCtaSelected(ctaValue: string): boolean {
  return selectedCtaValues.value.includes(ctaValue);
}

async function handleSave() {
  isSaving.value = true;

  // Save selected CTAs through the store
  await preCheckStore.setSelectedCTAs(
    props.creativeId,
    selectedCtaValues.value,
  );

  isOpen.value = false;
  isSaving.value = false;
}

const handleCancel = () => {
  isOpen.value = false;
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="865"
    closeButton
    useCustomClose
    @customClose="handleCancel"
    alignment="top"
  >
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.launchpad.cta-modal.title") }}

      <template #description>
        {{
          $t("funnel-flow.paid-social.launchpad.cta-modal.description", {
            max: maximumSelectable,
          })
        }}
      </template>

      <template #after>
        <Alert
          :type="isValidationPassed ? 'success' : 'warning'"
          class="tw:mt-6"
        >
          <span class="tw:flex tw:items-end tw:justify-between tw:gap-2">
            <span>
              <template v-if="isValidationPassed">
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.cta-modal.validation.passed",
                  )
                }}
              </template>
              <template v-else>
                <strong>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.cta-modal.validation.action-required-prefix",
                    )
                  }}
                </strong>
                <template v-if="selectedTotal > maximumSelectable">
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.cta-modal.validation.deselect-excess",
                      { count: excessCount },
                    )
                  }}
                </template>
                <template v-else>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.cta-modal.validation.select-at-least-one",
                    )
                  }}
                </template>
              </template>
            </span>

            <strong>{{
              $t("funnel-flow.paid-social.launchpad.common.selection-count", {
                current: selectedTotal,
                max: maximumSelectable,
              })
            }}</strong>
          </span>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <!-- Invalid CTAs Section -->
      <AdsLaunchpadModalSection v-if="invalidCTAs.length > 0">
        <template #title>
          {{
            $t(
              "funnel-flow.paid-social.launchpad.cta-modal.sections.cta-invalid",
            )
          }}
        </template>
        <AdsLaunchpadModalVisualAssetGrid :columns="3">
          <AdsLaunchpadModalTextCard
            v-for="cta in invalidCTAs"
            :key="cta.id"
            :selected="isCtaSelected(cta.value)"
            :readonly="readonly"
            @click="!readonly && toggleCta(cta.value)"
          >
            <template #title>
              {{ cta.label }}
            </template>

            <template #afterTitle>
              <Chip color="warning" variant="label">
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.cta-modal.sections.invalid",
                  )
                }}
              </Chip>
            </template>
          </AdsLaunchpadModalTextCard>
        </AdsLaunchpadModalVisualAssetGrid>
      </AdsLaunchpadModalSection>

      <!-- Valid CTAs Section -->
      <AdsLaunchpadModalSection v-if="validCTAs.length > 0">
        <template #title>
          {{
            $t(
              "funnel-flow.paid-social.launchpad.cta-modal.sections.add-valid-ctas",
            )
          }}
        </template>
        <AdsLaunchpadModalVisualAssetGrid :columns="3">
          <AdsLaunchpadModalTextCard
            v-for="cta in validCTAs"
            :key="cta.id"
            :selected="isCtaSelected(cta.value)"
            :readonly="readonly"
            @click="!readonly && toggleCta(cta.value)"
          >
            <template #title>
              {{ cta.label }}
            </template>
          </AdsLaunchpadModalTextCard>
        </AdsLaunchpadModalVisualAssetGrid>
      </AdsLaunchpadModalSection>
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
        type="button"
        :disabled="!isValidationPassed"
        :isLoading="isSaving"
        @click="handleSave"
      >
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
