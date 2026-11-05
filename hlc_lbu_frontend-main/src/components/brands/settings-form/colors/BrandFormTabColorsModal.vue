<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { BrandFormColor } from "../BrandFormTabColors.vue";
import { brandFormColorCategories } from "@/services/NewBrandsApi";
import { SelectOption } from "@/components/forms/base/FieldBaseNewSelect.vue";

interface Props {
  initialValues?: BrandFormColor;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  edit: [data: BrandFormColor];
  create: [data: BrandFormColor];
}>();

const { t } = useI18n();
const isOpen = defineModel<boolean>({ required: true });

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string().required(t("forms.required-field")).trim(),
      hex: string().required(t("forms.required-field")).trim(),
      category: string()
        .oneOf(brandFormColorCategories)
        .required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, resetForm } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: props.initialValues,
});

const isEditing = computed(() => props.initialValues?.id !== undefined);

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  if (isEditing.value && props.initialValues) {
    emit("edit", { ...values, id: props.initialValues.id });
  } else {
    emit("create", { ...values, id: new Date().getTime() });
  }

  // Close modal and reset form
  isOpen.value = false;
  resetForm({
    values: { name: undefined, hex: undefined, category: undefined },
  });
});

// Fill in values when editing
watch(
  () => props.initialValues,
  () =>
    resetForm({
      values: {
        category: undefined,
        hex: undefined,
        name: undefined,
        ...props.initialValues,
      },
    }),
);

const categoryOptions = computed<SelectOption[]>(() =>
  brandFormColorCategories.map((category) => ({
    label: t(`brands.settings.colors.categories.${category}`),
    value: category,
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
          ? $t("brands.settings.colors.modal.edit-title")
          : $t("brands.settings.colors.modal.add-title")
      }}

      <template #description>
        {{ $t("brands.settings.colors.modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldText
          name="name"
          :label="$t('brands.settings.colors.modal.name.label')"
          :placeholder="$t('brands.settings.colors.modal.name.placeholder')"
          required
        />

        <FieldText
          name="hex"
          :label="$t('brands.settings.colors.modal.hex.label')"
          :placeholder="$t('brands.settings.colors.modal.hex.placeholder')"
          required
        />

        <FieldNewSelect
          name="category"
          :label="$t('brands.settings.colors.modal.category.label')"
          :placeholder="$t('brands.settings.colors.modal.category.placeholder')"
          :options="categoryOptions"
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
            ? $t("brands.settings.colors.modal.update")
            : $t("brands.settings.colors.modal.add")
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
