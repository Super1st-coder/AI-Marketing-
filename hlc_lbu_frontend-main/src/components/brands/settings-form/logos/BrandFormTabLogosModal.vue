<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object, string } from "yup";
import { type BrandFormLogo } from "../BrandFormTabLogos.vue";
import { brandFormLogoCategories } from "@/services/NewBrandsApi";
import { SelectOption } from "@/components/forms/base/FieldBaseNewSelect.vue";

interface Props {
  initialValues?: BrandFormLogo;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  edit: [data: BrandFormLogo];
  create: [data: BrandFormLogo];
}>();

const { t } = useI18n();
const isOpen = defineModel<boolean>({ required: true });

const schema = computed(() =>
  toTypedSchema(
    object({
      image: mixed<File | string>().required(t("forms.required-field")),
      category: string()
        .oneOf(brandFormLogoCategories)
        .required(t("forms.required-field")),
      description: string().required(t("forms.required-field")).trim(),
      category_alias: string()
        .nullable()
        .when("category", {
          is: "custom",
          then: (schema) => schema.required(t("forms.required-field")).trim(),
        }),
    }),
  ),
);

const {
  handleSubmit,
  isSubmitting,
  resetForm,
  values,
  setFieldValue,
  resetField,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: props.initialValues,
});

const isEditing = computed(() => props.initialValues?.id !== undefined);

// Track if description was originally empty
const wasDescriptionEmpty = computed(
  () => !props.initialValues?.description?.trim(),
);

// Watch for category change to auto-fill description if it was originally empty
watch(
  () => values.category,
  (category, oldCategory) => {
    if (category && wasDescriptionEmpty.value) {
      setFieldValue(
        "description",
        t(`brands.settings.logos.categories.${category}.description`),
      );
    }
    // Clear alias when category changes away from "custom"
    if (oldCategory === "custom" && category !== "custom") {
      setFieldValue("category_alias", undefined);
    }
  },
);

// Watch for initialValues change to reset form
watch(
  () => props.initialValues,
  (initialValues) => {
    resetForm({
      values: {
        category: undefined,
        description: undefined,
        image: undefined,
        category_alias: undefined,
        ...initialValues,
      },
    });
  },
);

// Watch for initialValues change to reset form
watch(
  () => values.category,
  (category) => {
    if (category === "main-logo") {
      resetField("image", undefined);
    }
  },
);

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  if (isEditing.value && props.initialValues) {
    emit("edit", {
      ...values,
      id: props.initialValues.id,
      image_id: props.initialValues.image_id,
      source: props.initialValues.source,
      category_alias:
        values.category === "custom" ? values.category_alias : null,
    });
  } else {
    emit("create", {
      ...values,
      id: new Date().getTime(),
      category_alias:
        values.category === "custom" ? values.category_alias : null,
    });
  }

  // Close modal and reset form
  isOpen.value = false;
  resetForm({
    values: {
      category: undefined,
      description: undefined,
      image: undefined,
      category_alias: undefined,
    },
  });
});

const categoryOptions = computed<SelectOption[]>(() =>
  brandFormLogoCategories.map((category) => ({
    label: t(`brands.settings.logos.categories.${category}.title`),
    value: category,
  })),
);

// Get all categories with their titles and descriptions
const allCategoriesInfo = computed(() =>
  brandFormLogoCategories.map((category) => ({
    title: t(`brands.settings.logos.categories.${category}.title`),
    description: t(`brands.settings.logos.categories.${category}.description`),
  })),
);
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{
        isEditing
          ? $t("brands.settings.logos.modal.edit-title")
          : $t("brands.settings.logos.modal.add-title")
      }}

      <template #description>
        {{ $t("brands.settings.logos.modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldNewSelect
          name="category"
          :label="$t('brands.settings.logos.modal.category.label')"
          :placeholder="$t('brands.settings.logos.modal.category.placeholder')"
          :options="categoryOptions"
          required
        >
          <template #labelHelp>
            <div class="tw:space-y-3">
              <div v-for="category in allCategoriesInfo">
                <h5 class="tw:text-sm tw:font-semibold">
                  {{ category.title }}
                </h5>
                <p class="tw:text-xs">
                  {{ category.description }}
                </p>
              </div>
            </div>
          </template>
        </FieldNewSelect>

        <FieldImage
          name="image"
          :label="$t('brands.settings.logos.modal.image.label')"
          :disabled="isSubmitting"
          cropper
          required
          :previewAspectRatio="552 / 200"
          :acceptedFormats="BRAND_LOGO_ACCEPTED_FORMATS"
          :maxSize="BRAND_LOGO_MAX_FILE_SIZE_BYTES"
          :cropperAspectRatio="
            values.category === 'main-logo' ? 1 / 1 : undefined
          "
        >
          <template #inputTitle>{{
            $t("brands.settings.logos.modal.image.upload")
          }}</template>
        </FieldImage>

        <FieldText
          v-if="values.category === 'custom'"
          name="category_alias"
          :label="$t('brands.settings.logos.modal.alias.label')"
          :placeholder="$t('brands.settings.logos.modal.alias.placeholder')"
          required
        />

        <FieldTextarea
          name="description"
          :label="$t('brands.settings.logos.modal.description-field.label')"
          required
        />
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" @click="close" type="button">
        {{ $t("global.cancel") }}
      </Button>

      <Button :isLoading="isSubmitting" type="submit">
        {{
          isEditing
            ? $t("brands.settings.logos.modal.update")
            : $t("brands.settings.logos.modal.add")
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
