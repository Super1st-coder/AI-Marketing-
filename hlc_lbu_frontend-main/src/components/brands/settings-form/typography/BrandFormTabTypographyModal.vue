<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object, string } from "yup";
import { BrandFormTypography } from "../BrandFormTabTypography.vue";
import {
  brandFormTypographyStyles,
  brandFormTypographyUsages,
  type BrandFormTypographyStyle,
} from "@/services/NewBrandsApi";
import { SelectOption } from "@/components/forms/base/FieldBaseSelect.vue";

interface Props {
  initialValues?: BrandFormTypography;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  edit: [data: BrandFormTypography];
  create: [data: BrandFormTypography];
}>();

const { t } = useI18n();
const isOpen = defineModel<boolean>({ required: true });

const fontSchema = computed(() =>
  object({
    style: string()
      .oneOf(brandFormTypographyStyles)
      .required(t("forms.required-field")),
    file: mixed<File | string>().required(t("forms.required-field")),
    usage: string()
      .oneOf(brandFormTypographyUsages)
      .required(t("forms.required-field")),
  }),
);

const schema = computed(() =>
  toTypedSchema(
    object({
      fontFamily: string().required(t("forms.required-field")).trim(),
      fonts: array().of(fontSchema.value).required(t("forms.required-field")),
    }),
  ),
);

const emptyFonts = [
  {
    style: "light" as const,
    usage: "body" as const,
    file: undefined,
  },
  {
    style: "regular" as const,
    usage: "body" as const,
    file: undefined,
  },
  {
    style: "medium" as const,
    usage: "body" as const,
    file: undefined,
  },
  {
    style: "bold" as const,
    usage: "headings" as const,
    file: undefined,
  },
];

const { handleSubmit, isSubmitting, values, resetForm, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      ...props.initialValues,
      // @ts-expect-error
      fonts: props.initialValues?.fonts ?? emptyFonts,
    },
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
    values: {
      fontFamily: undefined,
      // @ts-expect-error
      fonts: emptyFonts,
    },
  });
});

// Fill in values when editing
watch(
  () => props.initialValues,
  () =>
    resetForm({
      values: {
        fontFamily: undefined,
        // @ts-expect-error
        fonts: emptyFonts,
        ...props.initialValues,
      },
    }),
);

const usageOptions = computed<SelectOption[]>(() =>
  brandFormTypographyUsages.map((category) => ({
    label: t(`brands.settings.typography.usages.${category}.description`),
    value: category,
  })),
);

const styleOptions = computed<SelectOption[]>(() =>
  brandFormTypographyStyles.map((style) => ({
    label: t(`brands.settings.typography.styles.${style}`),
    value: style,
  })),
);

// Get available style options for a specific font index
const getAvailableStyleOptions = (currentIndex: number): SelectOption[] => {
  if (!values.fonts) return styleOptions.value;

  // Get styles used by other fonts (not the current one)
  const usedStyles = values.fonts
    .map((font, index) => (index !== currentIndex ? font.style : undefined))
    .filter((style) => style !== undefined);

  // Filter options to show only unused styles + current style
  const currentStyle = values.fonts[currentIndex]?.style;
  return styleOptions.value.filter(
    (option) =>
      !usedStyles.includes(option.value as BrandFormTypographyStyle) ||
      option.value === currentStyle,
  );
};

const handleDeleteFont = (index: number) => {
  if (values.fonts && values.fonts.length > 1) {
    const newFonts = values.fonts.filter((_, i) => i !== index);
    setFieldValue("fonts", newFonts);
  }
};

const handleAddFont = () => {
  if (values.fonts) {
    // Get all currently used styles
    const usedStyles = values.fonts.map((font) => font.style);

    // Find the first unused style, or default to "regular"
    const availableStyle =
      brandFormTypographyStyles.find((style) => !usedStyles.includes(style)) ||
      "regular";

    const newFonts = [
      ...values.fonts,
      {
        style: availableStyle,
        usage: "body" as const,
        file: undefined as NonNullable<undefined>,
      },
    ];
    setFieldValue("fonts", newFonts);
  }
};

// Check if all styles are used
const canAddMoreStyles = computed(() => {
  if (!values.fonts) return true;
  return values.fonts.length < brandFormTypographyStyles.length;
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="800"
    closeButton
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{
        isEditing
          ? $t("brands.settings.typography.modal.edit-title")
          : $t("brands.settings.typography.modal.add-title")
      }}

      <template #description>
        {{ $t("brands.settings.typography.modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldText
          name="fontFamily"
          :label="$t('brands.settings.typography.modal.font-family.label')"
          :placeholder="
            $t('brands.settings.typography.modal.font-family.placeholder')
          "
          required
        />

        <VDataTable
          v-if="values.fonts"
          :items="values.fonts"
          :headers="[
            {
              title: $t('brands.settings.typography.modal.table.font-style'),
              key: 'style',
              sortable: false,
              width: 160,
            },
            {
              title: $t('brands.settings.typography.modal.table.file'),
              key: 'file',
              sortable: false,
            },
            {
              title: $t('brands.settings.typography.modal.table.usage'),
              key: 'usage',
              sortable: false,
              width: 160,
            },
            {
              title: '',
              key: 'actions',
              sortable: false,
              width: 60,
            },
          ]"
        >
          <template v-slot:item.style="{ index }">
            <FieldSelect
              :name="`fonts[${index}].style`"
              :placeholder="
                $t('brands.settings.typography.modal.style-placeholder')
              "
              :options="getAvailableStyleOptions(index)"
            />
          </template>

          <template v-slot:item.file="{ index }">
            <FieldFile
              :name="`fonts[${index}].file`"
              :label="$t('brands.settings.typography.modal.upload-label')"
              :acceptedExtensions="
                BRAND_TYPOGRAPHY_ACCEPTED_FORMATS.map(
                  (format) => `.${format}`,
                ).join(',')
              "
              :maxSize="BRAND_TYPOGRAPHY_MAX_FILE_SIZE_BYTES"
              class="tw:py-5 tw:pr-10"
            />
          </template>

          <template v-slot:item.usage="{ index }">
            <FieldSelect
              :name="`fonts[${index}].usage`"
              :placeholder="
                $t('brands.settings.typography.modal.usage-placeholder')
              "
              :options="usageOptions"
            />
          </template>

          <template v-slot:item.actions="{ index }">
            <Button
              v-if="values.fonts && values.fonts.length > 1"
              variant="outlined"
              color="secondary"
              icon="tabler-trash"
              size="md"
              type="button"
              @click="handleDeleteFont(index)"
            />
          </template>

          <template #bottom>
            <Tooltip
              :disabled="canAddMoreStyles"
              :maxWidth="300"
              placement="bottom-start"
            >
              <Button
                variant="text"
                color="secondary"
                left-icon="tabler-plus"
                type="button"
                @click="handleAddFont"
                class="tw:self-start"
                :disabled="!canAddMoreStyles"
              >
                {{ $t("brands.settings.typography.modal.add-new-style") }}
              </Button>

              <template #content>
                {{ $t("brands.settings.typography.modal.all-styles-used") }}
              </template>
            </Tooltip>
          </template>
        </VDataTable>
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" @click="close" type="button">
        {{ $t("global.cancel") }}
      </Button>

      <Button :isLoading="isSubmitting" type="submit">
        {{
          isEditing
            ? $t("brands.settings.typography.modal.update")
            : $t("brands.settings.typography.modal.add")
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
