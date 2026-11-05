<script setup lang="ts">
import { computed } from "vue";
import BrandsApi from "@/services/BrandsApi";
import { ProyectData } from "@/services/projects/ProjectsApi";

const { t } = useI18n();

const brandId = useBrandId();
const brand = (await BrandsApi.getOne(brandId)).data;

export type ProjectFormData = ProyectData;
const props = defineProps<{
  data?: ProjectFormData;
}>();
const authStore = useAuthStore();

const userHas = (step: FormStep) => {
  if (!step.requires) return true;

  return authStore.hasPermissionFor(step.requires);
};

const steps = computed<FormStep[]>(() => [
  {
    name: "information",
    label: t("projects.information.title"),
    icon: "tabler-book",
    requires: [{ name: "PROJECT", actions: ["R", "C", "U"] }],
  },
  {
    name: "product",
    label: t("projects.product.sidebar-title"),
    icon: "tabler:box",
    requires: [{ name: "PROJECT", actions: ["R", "C", "U"] }],
  },
  {
    name: "targetCustomer",
    label: t("projects.target-customer.sidebar-title"),
    icon: "tabler:target",
    requires: [{ name: "PROJECT", actions: ["R", "C", "U"] }],
  },
  {
    name: "summary",
    label: t("projects.summary.title"),
    icon: "tabler-file-text",
    requires: [{ name: "PROJECT", actions: ["R"] }],
  },
]);

const initialStep = computed<number>(() => {
  // Values of "step":
  // After creating the project / After updating the product = 0
  // After setting a product = 1
  // After setting a buyer person = 2
  // After saving summary = 3

  if (props.data?.step != undefined) {
    switch (props.data.step) {
      case 0:
        return 1;
      case 1:
        return 2;
      case 2:
        return 3;
      case 3:
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
  id: (data) => `project-${data?.id}`,
  filterStep: (step) => userHas(step),
});
</script>

<template>
  <MultiStepForm>
    <template #sidebarHeader>
      <template v-if="data">
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("projects.project") }}
        </SidebarTitle>

        <SidebarTitle>
          {{ data.name }}
        </SidebarTitle>
      </template>
      <template v-else>
        <SidebarTitle>
          {{ $t("projects.create-project") }}
        </SidebarTitle>
      </template>
    </template>

    <template #sidebarFooter>
      <SidebarLink
        :to="{ name: 'ProjectList' }"
        variant="link"
        icon="tabler-arrow-left"
      >
        {{ $t("brands.back-to-brand", { name: brand.name }) }}
      </SidebarLink>
    </template>

    <FormStep name="information">
      <ProjectFormInformation />
    </FormStep>

    <FormStep name="product">
      <ProjectFormProduct />
    </FormStep>

    <FormStep name="targetCustomer">
      <ProjectFormTargetCustomer />
    </FormStep>

    <FormStep name="summary">
      <ProjectFormSummary />
    </FormStep>
  </MultiStepForm>
</template>
