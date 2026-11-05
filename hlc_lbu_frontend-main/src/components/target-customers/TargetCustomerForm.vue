<script setup lang="ts">
import BrandsApi from "@/services/BrandsApi";
import { BuyerPersonData } from "@/services/BuyerPersonasApi";
import ProjectsApi from "@/services/projects/ProjectsApi";
import { useRouteQuery } from "@vueuse/router";

const brandId = useBrandId();
const brand = (await BrandsApi.getOne(brandId)).data;

export type TargetCustomerFormData = BuyerPersonData & {
  brandId: number;
  files?: File[];
};

const { t } = useI18n();

const props = defineProps<{
  data?: TargetCustomerFormData;
}>();

const authStore = useAuthStore();

const { targetProjectId, targetProjectRoute } = useProjectQueryShorcut();
const targetProject = targetProjectId.value
  ? (await ProjectsApi.getOne(brandId, targetProjectId.value)).data
  : undefined;
const newImageGeneration = useRouteQuery<string, string | undefined>(
  "newImageGeneration",
  undefined,
);
const useNewImageGeneration = computed(
  () => newImageGeneration.value === "true",
);

const userHas = (step: FormStep) => {
  if (!step.requires) return true;

  return authStore.hasPermissionFor(step.requires);
};

const steps = computed<FormStep[]>(() => [
  {
    name: "information",
    label: t("buyer-person.information.title"),
    icon: "tabler-book",
    requires: [{ name: "TARGET_CUSTOMER", actions: ["R", "C", "U"] }],
  },
  {
    name: "refine",
    label: t("buyer-person.refine.title"),
    icon: "tabler-files",
    requires: [{ name: "TARGET_CUSTOMER", actions: ["R", "C", "U"] }],
  },
  {
    name: "image",
    label: t("buyer-person.image.title"),
    icon: "tabler:photo",
    requires: [{ name: "TARGET_CUSTOMER", actions: ["R", "C", "U"] }],
  },
  {
    name: "summary",
    label: t("buyer-person.summary.title"),
    icon: "tabler-file-text",
    requires: [{ name: "TARGET_CUSTOMER", actions: ["R"] }],
  },
]);

const initialStep = computed<number>(() => {
  // Values of "step":
  // 0 - Define Buyer Person
  // 0 - Update Buyer Person
  // 1 - Setting Product By Buyer Person
  // 1 - Upload Docs
  // 2 - Generate Attributes
  // 3 - Save Attributes
  // 4 - Generate Image Attributes
  // 4 - Save Image Attributes
  // 4 - Generate Image Prompts
  // 4 - Set Preferred Image Prompt
  // 4 - Save Preferred Image Prompt
  // 5 - Upload image
  // 6 - Save Complete Buyer

  if (props.data?.step != undefined) {
    switch (props.data.step) {
      case 0:
        return 0;
      case 1:
        return 0;
      case 2:
        return 1;
      case 3:
        return 2;
      case 4:
        return 2;
      case 5:
        return 3;
      case 6:
        return 3;
      default:
        return 0;
    }
  }

  return 0;
});

// Initialize the multi-step form
const { data } = useMultiStepForm(steps, {
  useLocalStorage: true,
  initialData: props.data,
  initialStep: initialStep,
  id: (data) => `target-customer-${data?.id}`,
  filterStep: (step) => userHas(step),
});
</script>

<template>
  <MultiStepForm>
    <template #sidebarHeader>
      <template v-if="data">
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("buyer-person.target-customer") }}
        </SidebarTitle>

        <SidebarTitle>
          {{ data.name }}
        </SidebarTitle>
      </template>
      <template v-else>
        <SidebarTitle>
          {{ $t("buyer-person.create-target-customer") }}
        </SidebarTitle>
      </template>
    </template>

    <template #sidebarFooter>
      <SidebarLink
        v-if="targetProjectRoute"
        :to="targetProjectRoute"
        variant="link"
        icon="tabler-arrow-left"
        replace
      >
        {{ $t("projects.back-to-project", { name: targetProject?.name }) }}
      </SidebarLink>
      <SidebarLink
        v-else
        :to="{ name: 'BuyerPersonList' }"
        variant="link"
        icon="tabler-arrow-left"
      >
        {{ $t("brands.back-to-brand", { name: brand.name }) }}
      </SidebarLink>
    </template>

    <FormStep name="information">
      <TargetCustomerFormInformation />
    </FormStep>

    <FormStep name="refine">
      <TargetCustomerFormRefine />
    </FormStep>

    <FormStep name="image">
      <template v-if="useNewImageGeneration">
        <TargetCustomerFormImage />
      </template>
      <template v-else>
        <LegacyTargetCustomerFormImage />
      </template>
    </FormStep>

    <FormStep name="summary">
      <TargetCustomerFormSummary />
    </FormStep>
  </MultiStepForm>
</template>
