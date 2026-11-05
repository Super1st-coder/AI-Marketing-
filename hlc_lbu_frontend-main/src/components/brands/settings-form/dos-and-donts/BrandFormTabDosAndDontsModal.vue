<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object, string } from "yup";
import { brandFormRuleTypes } from "@/services/NewBrandsApi";
import { BrandFormRule } from "../BrandFormTabDosAndDonts.vue";

interface Props {
  initialValues?: BrandFormRule;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  edit: [data: BrandFormRule];
  create: [data: BrandFormRule];
}>();

const { t } = useI18n();
const isOpen = defineModel<boolean>({ required: true });

const schema = computed(() =>
  toTypedSchema(
    object({
      type: string()
        .oneOf(brandFormRuleTypes)
        .required(t("forms.required-field")),
      text: string().required(t("forms.required-field")).trim(),
      image: mixed<File | string>(),
    }),
  ),
);

const { handleSubmit, isSubmitting, resetForm, values, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: { type: "do", ...props.initialValues },
  });

const isEditing = computed(() => props.initialValues?.id !== undefined);

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  if (isEditing.value && props.initialValues) {
    emit("edit", { ...values, id: props.initialValues.id });
  } else {
    const brand = { ...values, id: new Date().getTime() };
    emit("create", brand);
  }

  // Close modal and reset form
  isOpen.value = false;
  resetForm({
    values: { type: "do", text: undefined, image: undefined },
  });
});

// Fill in values when editing
watch(
  () => props.initialValues,
  () => {
    if (props.initialValues) {
      resetForm({
        values: props.initialValues,
      });
    } else {
      resetForm({
        values: { text: undefined, image: undefined },
      });
    }
  },
  { immediate: true },
);

// Reset when modal closes
watch(isOpen, (newValue) => {
  if (!newValue) {
    resetForm({
      values: { type: "do", text: undefined, image: undefined },
    });
  }
});
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
          ? $t("brands.settings.dos-and-donts.modal.edit-title")
          : $t("brands.settings.dos-and-donts.modal.add-title")
      }}

      <template #description>
        {{ $t("brands.settings.dos-and-donts.modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <!-- Rule Type Toggle -->
        <div class="tw:flex tw:flex-col tw:gap-2.5">
          <FieldLabel>{{
            $t("brands.settings.dos-and-donts.modal.rule-type.label")
          }}</FieldLabel>
          <div
            class="border tw:flex tw:gap-1 tw:rounded-xl tw:border-gray-200 tw:bg-[#F7F5F3] tw:p-1"
          >
            <Button
              :variant="values.type === 'do' ? 'outlined' : 'text'"
              color="secondary"
              type="button"
              class="tw:flex-1"
              @click="setFieldValue('type', 'do')"
            >
              {{ $t("brands.settings.dos-and-donts.modal.rule-type.do") }}
            </Button>
            <Button
              :variant="values.type === 'dont' ? 'outlined' : 'text'"
              color="secondary"
              type="button"
              class="tw:flex-1"
              @click="setFieldValue('type', 'dont')"
            >
              {{ $t("brands.settings.dos-and-donts.modal.rule-type.dont") }}
            </Button>
          </div>
        </div>

        <!-- Image Upload -->
        <FieldImage
          name="image"
          :label="$t('brands.settings.dos-and-donts.modal.image.label')"
          cropper
          :previewAspectRatio="552 / 200"
          :maxSize="BRAND_DOS_DONTS_IMAGE_MAX_FILE_SIZE_BYTES"
        />

        <!-- Rule Text -->
        <FieldTextarea
          name="text"
          :label="$t('brands.settings.dos-and-donts.modal.text.label')"
          :placeholder="
            $t('brands.settings.dos-and-donts.modal.text.placeholder')
          "
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
            ? $t("brands.settings.dos-and-donts.modal.update")
            : $t("brands.settings.dos-and-donts.modal.add")
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
