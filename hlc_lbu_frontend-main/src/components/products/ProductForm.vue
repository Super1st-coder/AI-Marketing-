<script setup lang="ts">
import { ProductData } from "@/services/ProductsApi";
import SidebarLink from "../navigation/SidebarLink.vue";
import BrandsApi from "@/services/BrandsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";

const brandId = useBrandId();
const brand = (await BrandsApi.getOne(brandId)).data;

export type ProductFormData = ProductData & {
  files?: File[];
  refinerOpenCategory?: string;
};

const props = defineProps<{
  data?: ProductFormData;
}>();

const { t } = useI18n();

const { targetProjectId, targetProjectRoute } = useProjectQueryShorcut();
const targetProject = targetProjectId.value
  ? (await ProjectsApi.getOne(brandId, targetProjectId.value)).data
  : undefined;
const authStore = useAuthStore();

const userHas = (step: FormStep) => {
  if (!step.requires) return true;

  return authStore.hasPermissionFor(step.requires);
};

const steps = computed<FormStep[]>(() => [
  {
    name: "information",
    label: t("products.information.title"),
    icon: "tabler-book",
    requires: [{ name: "PRODUCT", actions: ["R", "C", "U"] }],
  },
  {
    name: "image",
    label: t("products.image.sidebar-title"),
    icon: "tabler-photo",
    requires: [{ name: "PRODUCT", actions: ["R", "C", "U"] }],
  },
  {
    name: "refine",
    label: t("products.refine.sidebar-title"),
    icon: "tabler-files",
    requires: [{ name: "PRODUCT", actions: ["R", "C", "U"] }],
  },
  {
    name: "summary",
    label: t("products.summary.title"),
    icon: "tabler-file-text",
    requires: [{ name: "PRODUCT", actions: ["R"] }],
  },
]);

const initialStep = computed<number>(() => {
  // Values of "step":
  // After creating a product = 0
  // After generating mandatory and optional attributes = 1
  // After saving attributes = 2
  // After completing product/saving story = 3

  if (props.data?.step != undefined) {
    switch (props.data.step) {
      case 0:
        return 0;
      case 1:
        return props.data.images && props.data.images.length > 0 ? 2 : 1;
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
  id: (data) => `product-${data?.id}`,
  filterStep: (step) => userHas(step),
});
</script>

<template>
  <MultiStepForm>
    <template #sidebarHeader>
      <template v-if="data">
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("products.product") }}
        </SidebarTitle>

        <SidebarTitle>
          {{ data.name }}
        </SidebarTitle>
      </template>
      <template v-else>
        <SidebarTitle>
          {{ $t("products.create-product") }}
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
        :to="{ name: 'ProductList' }"
        variant="link"
        icon="tabler-arrow-left"
      >
        {{ $t("brands.back-to-brand", { name: brand.name }) }}
      </SidebarLink>
    </template>

    <FormStep name="information">
      <ProductFormInformation />
    </FormStep>

    <FormStep name="image">
      <ProductFormImage />
    </FormStep>

    <FormStep name="refine">
      <ProductFormRefine />
    </FormStep>

    <FormStep name="summary">
      <ProductFormSummary />
    </FormStep>
  </MultiStepForm>
</template>
