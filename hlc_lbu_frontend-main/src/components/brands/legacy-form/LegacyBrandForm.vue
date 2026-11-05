<script setup lang="ts">
import { BrandData } from "@/services/BrandsApi";

export type BrandFormData = BrandData & {
  image?: Blob;
};

const props = defineProps<{
  data?: BrandFormData;
}>();

const { t } = useI18n();

const steps = computed<FormStep[]>(() => [
  {
    name: "identity",
    label: t("brands.identity.title"),
    icon: "tabler:id",
  },
  {
    name: "vision",
    label: t("brands.vision.title"),
    icon: "tabler-eye",
  },
  {
    name: "uniqueness",
    label: t("brands.uniqueness.title"),
    icon: "tabler-stars",
  },
  {
    name: "markets",
    label: t("brands.markets.title"),
    icon: "tabler:shopping-cart",
  },
  {
    name: "summary",
    label: t("brands.summary.title"),
    icon: "tabler-file-text",
  },
]);

const initialStep = computed<number>(() => {
  if (props.data?.step != undefined) {
    return Math.min(props.data.step + 1, steps.value.length - 1);
  }

  return 0;
});

// Initialize the multi-step form
const { data } = useMultiStepForm(steps, {
  useLocalStorage: true,
  initialData: props.data,
  initialStep: initialStep,
  id: (data) => `brand-${data?.id}`,
});
</script>

<template>
  <MultiStepForm>
    <template #sidebarHeader>
      <template v-if="data">
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("brands.brand") }}
        </SidebarTitle>

        <SidebarTitle>
          {{ data.name }}
        </SidebarTitle>
      </template>
      <template v-else>
        <SidebarTitle>
          {{ $t("brands.create-brand") }}
        </SidebarTitle>
      </template>
    </template>

    <template #sidebarFooter>
      <SidebarLink
        :to="{ name: 'BrandList' }"
        variant="link"
        icon="tabler-arrow-left"
      >
        {{ t("brands.return-to-brands") }}
      </SidebarLink>
    </template>

    <FormStep name="identity">
      <LegacyBrandFormIdentity />
    </FormStep>

    <FormStep name="vision">
      <LegacyBrandFormVision />
    </FormStep>

    <FormStep name="uniqueness">
      <LegacyBrandFormUniqueness />
    </FormStep>

    <FormStep name="markets">
      <LegacyBrandFormMarkets />
    </FormStep>

    <FormStep name="summary">
      <LegacyBrandFormSummary />
    </FormStep>
  </MultiStepForm>
</template>
