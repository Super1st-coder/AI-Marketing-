<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { ProductFormData } from "./ProductForm.vue";
import ProductsApi from "@/services/ProductsApi";
import { getSummaryRefinerCategories } from "../forms/category-refiner/categoryRefinerTypes";
import { productRefinerStyles } from "./productContants";

const { t } = useI18n();
const brandId = useBrandId();

const router = useRouter();
const { targetProjectRoute } = useProjectQueryShorcut();

const { data, goBack, goToStep } = useMultiStepFormContext<ProductFormData>();

// cuando se hace click en el icono de editar de una categoria, recordar que categoria abrir en el paso Refine y volver
function handleEditCategory(categoryName: string) {
  // marca la categoria que se va a editar antes de volver al paso anterior
  (data.value as ProductFormData).refinerOpenCategory = categoryName;
  goBack();
}

const mandatoryCategories = getSummaryRefinerCategories(
  data.value.mandatory_attributes_saved,
  data.value.mandatory_attributes_generated,
);
const optionalCategories = getSummaryRefinerCategories(
  data.value.optional_attributes_saved,
  data.value.optional_attributes_generated,
);

const schema = computed(() =>
  toTypedSchema(
    object({
      product_story: string().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    product_story: data.value.product_story ?? undefined,
  },
});

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  if (!data.value.locked) {
    const productId = data.value.id;

    // Update product story
    await ProductsApi.completeProduct(brandId, productId, values.product_story);
  }

  // Disable the save alert
  disableSaveAlert.value = true;

  if (targetProjectRoute.value) {
    // Navigate to the project
    router.replace(targetProjectRoute.value);
  } else {
    // Navigate to the product list
    router.push({ name: "ProductList" });
  }
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :maxWidth="1130">
    <div class="tw:flex tw:flex-col tw:gap-5 tw:lg:flex-row tw:lg:items-start">
      <CardBase
        class="tw:shrink-0 tw:grow tw:md:top-[66px] tw:lg:sticky tw:lg:order-last tw:lg:max-w-[331px]"
      >
        <div class="tw:p-4">
          <ImageSlider
            v-if="data.images?.length"
            :images="data.images.map((image) => image.url)"
          />
        </div>

        <template v-if="!data.locked">
          <Separator />

          <div class="tw:p-4">
            <Button
              class="tw:w-full"
              size="sm"
              color="secondary"
              variant="outlined"
              leftIcon="tabler:pencil"
              type="button"
              @click="goToStep(1)"
            >
              Edit Product Image
            </Button>
          </div>
        </template>
      </CardBase>

      <div class="tw:grid tw:grow tw:grid-cols-1 tw:gap-10">
        <CardBase>
          <div class="tw:p-6">
            <PageTitle
              helpButton
              helpVideoUrl="https://www.youtube.com/watch?v=eGiR2Igu_vU"
              size="lg"
              class="tw:mb-2"
            >
              {{ data.name }}
            </PageTitle>

            <a
              v-if="data.product_url"
              :href="data.product_url"
              target="_blank"
              rel="noopener noreferrer"
              class="tw:flex tw:items-center tw:text-sm tw:font-medium tw:break-all tw:text-gray-600 tw:hover:text-blue-600 tw:hover:underline"
            >
              <Icon icon="mdi:web" class="tw:mr-2 tw:shrink-0 tw:text-[20px]" />

              {{ data.product_url }}
            </a>
          </div>

          <Separator />

          <div class="tw:p-6">
            <EditableCardSection
              name="product_story"
              :title="t('products.summary.product-story')"
              icon="tabler:file-description"
              :editable="!data.locked"
              class="tw:w-full tw:lg:order-first tw:lg:grow"
              :disabled="data?.locked || isSubmitting"
            />
          </div>
        </CardBase>

        <div class="tw:grid tw:grow tw:grid-cols-1 tw:gap-6">
          <CategoryRefinerSummary
            :categories="mandatoryCategories"
            :styles="productRefinerStyles"
            @edit="handleEditCategory"
            :editable="!data?.locked"
          >
            <template #title>{{ t("refiner.mandatory-categories") }}</template>
          </CategoryRefinerSummary>

          <CategoryRefinerSummary
            :categories="optionalCategories"
            :styles="productRefinerStyles"
            @edit="handleEditCategory"
            :editable="!data?.locked"
          >
            <template #title>{{ t("refiner.optional-categories") }}</template>
          </CategoryRefinerSummary>
        </div>
      </div>
    </div>

    <template #actions>
      <WizardCardActions>
        <PermissionGuard :requires="[{ name: 'PRODUCT', actions: ['U'] }]">
          <ButtonGoBack @click="goBack" />
          <ButtonNext :isLoading="isSubmitting">
            {{
              data.locked
                ? t("products.summary.back-to-products")
                : t("global.save")
            }}
          </ButtonNext>
        </PermissionGuard>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
