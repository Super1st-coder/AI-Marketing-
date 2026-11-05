<script setup lang="ts">
import BrandsApi from "@/services/BrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object, string } from "yup";
import { BrandFormData } from "./LegacyBrandForm.vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const router = useRouter();

const { goBack, data } = useMultiStepFormContext<BrandFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      vision: string().required(t("forms.required-field")).trim(),
      markets: string().required(t("forms.required-field")).trim(),
      industry: string().required(t("forms.required-field")).trim(),
      geography: string().required(t("forms.required-field")).trim(),
      uniqueness: string().required(t("forms.required-field")).trim(),
      image: mixed<Blob>().required(t("forms.required-field")),
      story: string().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    vision:
      data.value.attributes_saved?.vision ??
      data.value.attributes_generated?.vision ??
      data.value.vision ??
      undefined,
    markets: data.value.markets ?? undefined,
    industry: data.value.industry ?? undefined,
    geography: data.value.geography ?? undefined,
    uniqueness:
      data.value.attributes_saved?.uniqueness ??
      data.value.attributes_generated?.uniqueness ??
      data.value.uniqueness ??
      undefined,
    image: data.value?.image,
    story:
      data.value.attributes_saved?.story ??
      data.value.attributes_generated?.story,
  },
});

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  const brandId = data.value.id;

  // Update existing brand
  await BrandsApi.updateByStep(brandId, {
    attributes_generated: data.value.attributes_generated,
    attributes_saved: {
      vision: values.vision,
      uniqueness: values.uniqueness,
      story: values.story,
    },
    industry: values.industry,
    markets: values.markets,
    geography: values.geography,
    step: 4,
  });

  // Update image
  BrandsApi.uploadImage(brandId, values.image);

  // Disable the save alert
  disableSaveAlert.value = true;

  // Navigate to the brand
  router.push({ name: "Brand", params: { brandId: data.value.id } });
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit">
    <div class="tw:flex tw:flex-col tw:justify-between tw:gap-8 tw:lg:flex-row">
      <FieldImage
        name="image"
        required
        cropper
        :cropperAspectRatio="1 / 1"
        class="tw:w-full tw:shrink-0 tw:lg:order-last tw:lg:basis-[354px]"
        :disabled="isSubmitting"
      />

      <div class="tw:flex tw:grow tw:flex-col tw:gap-4">
        <h1 class="tw:text-[38px] tw:font-extrabold tw:lg:text-[38px]">
          {{ data.name }}
        </h1>

        <div
          v-if="data.website"
          class="tw:ml-1 tw:flex tw:items-center tw:text-gray-600"
        >
          <Icon icon="mdi:web" class="tw:mr-2 tw:h-6 tw:w-8" />
          {{ data.website }}
        </div>

        <EditableCardSection
          name="story"
          :title="t('brands.summary.brand-description.label')"
          :placeholder="t('brands.summary.brand-description.placeholder')"
          icon="tabler:file-description"
          editable
          :disabled="isSubmitting"
        />
      </div>
    </div>

    <div class="tw:grid tw:gap-5 tw:lg:grid-cols-3">
      <CardBase class="tw:p-5">
        <EditableCardSection
          name="vision"
          :title="t('brands.summary.brand-vision.label')"
          :placeholder="t('brands.summary.brand-vision.placeholder')"
          icon="tabler-eye"
          iconVariant="success"
          editable
          required
          :disabled="isSubmitting"
        />
      </CardBase>

      <CardBase class="tw:p-5">
        <EditableCardSection
          name="uniqueness"
          :title="t('brands.summary.brand-uniqueness.label')"
          :placeholder="t('brands.summary.brand-uniqueness.placeholder')"
          icon="tabler-stars"
          iconVariant="primary"
          editable
          required
          :disabled="isSubmitting"
        />
      </CardBase>

      <CardBase class="tw:p-5">
        <CardTitle
          icon="tabler-speakerphone"
          iconVariant="success"
          class="tw:mb-3"
          required
        >
          {{ t("brands.summary.brand-markets") }}
        </CardTitle>

        <div class="tw:flex tw:flex-col tw:gap-5">
          <div>
            <li class="tw:mb-1 tw:list-none tw:font-bold">
              {{ t("brands.summary.industry.label") }}
            </li>
            <FieldEditableText
              name="industry"
              required
              :placeholder="t('brands.summary.industry.placeholder')"
              :disabled="isSubmitting"
            />
          </div>

          <div>
            <li class="tw:mb-1 tw:list-none tw:font-bold">
              {{ t("brands.summary.markets.label") }}
            </li>
            <FieldEditableText
              name="markets"
              required
              :placeholder="t('brands.summary.markets.placeholder')"
              :disabled="isSubmitting"
            />
          </div>

          <div>
            <li class="tw:mb-1 tw:list-none tw:font-bold">
              {{ t("brands.summary.geography.label") }}
            </li>
            <FieldEditableText
              name="geography"
              required
              :placeholder="t('brands.summary.geography.placeholder')"
              :disabled="isSubmitting"
            />
          </div>
        </div>
      </CardBase>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting">
          {{ t("global.save") }}
        </ButtonNext>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
