<script setup lang="ts">
import {
  BrandFormTypography,
  type BrandFormTypographyFont,
} from "../BrandFormTabTypography.vue";
import {
  brandFormTypographyStyles,
  brandFormTypographyUsages,
  type BrandFormTypographyStyle,
} from "@/services/NewBrandsApi";

interface Props {
  typography: BrandFormTypography;
}

const props = defineProps<Props>();
const { t } = useI18n();

const emit = defineEmits<{
  edit: [logo: BrandFormTypography];
  delete: [typography: BrandFormTypography, fontIndex: number];
}>();

const handleEdit = () => {
  emit("edit", props.typography);
};

const handleDelete = (fontIndex: number) => {
  emit("delete", props.typography, fontIndex);
};

const hasFontFamily = computed(() => !!props.typography.fontFamily?.trim());

const hasFontFile = (font: BrandFormTypographyFont) => !!font.file;

const hasValidStyle = (font: BrandFormTypographyFont) =>
  brandFormTypographyStyles.includes(font.style);

const hasValidUsage = (font: BrandFormTypographyFont) =>
  brandFormTypographyUsages.includes(font.usage);

const hasValidStyles = computed(() =>
  props.typography.fonts.every((font) => hasValidStyle(font)),
);

const hasValidUsages = computed(() =>
  props.typography.fonts.every((font) => hasValidUsage(font)),
);

const hasValidFiles = computed(() =>
  props.typography.fonts.every((font) => hasFontFile(font)),
);

const isCompleted = computed(
  () =>
    hasFontFamily.value &&
    hasValidStyles.value &&
    hasValidUsages.value &&
    hasValidFiles.value,
);

const supportedFormatsText = computed(() =>
  BRAND_TYPOGRAPHY_ACCEPTED_FORMATS.map((format) =>
    t(`forms.file-upload.formats.${format}`),
  ).join(", "),
);

const maxTypographySizeText = computed(() =>
  formatFileSize(BRAND_TYPOGRAPHY_MAX_FILE_SIZE_BYTES),
);

const fontWeightClassByStyle: Record<BrandFormTypographyStyle, string> = {
  thin: "tw:font-thin",
  "extra-light": "tw:font-extralight",
  light: "tw:font-light",
  regular: "tw:font-normal",
  medium: "tw:font-medium",
  "semi-bold": "tw:font-semibold",
  bold: "tw:font-bold",
  "extra-bold": "tw:font-extrabold",
  black: "tw:font-black",
  italic: "tw:font-normal tw:italic",
};

const getFontWeightClass = (style: BrandFormTypographyStyle) =>
  fontWeightClassByStyle[style];
</script>

<template>
  <CardBase
    v-for="(font, fontIndex) in typography.fonts"
    :key="`${typography.id}-${font.id ?? fontIndex}`"
    class="tw:p-4"
    borderRadius="md"
  >
    <!-- Header -->
    <div class="tw:mb-2.5 tw:flex tw:items-center tw:gap-3.5">
      <!-- Name/Font family -->
      <h3 :class="['tw:text-lg', getFontWeightClass(font.style)]">
        {{ typography.fontFamily }}
      </h3>

      <!-- Warning -->
      <Tooltip v-if="!isCompleted" placement="top" :maxWidth="213">
        <Icon
          icon="tabler:alert-triangle"
          class="tw:text-2xl tw:text-warning"
        />

        <template #content>
          {{
            !hasFontFamily
              ? $t("brands.settings.typography.warnings.missing-family")
              : !hasValidStyles
                ? $t("brands.settings.typography.warnings.invalid-style")
                : !hasValidUsages
                  ? $t("brands.settings.typography.warnings.invalid-usage")
                  : $t("brands.settings.typography.warnings.missing-file", {
                      formats: supportedFormatsText,
                      maxSize: maxTypographySizeText,
                    })
          }}
        </template>
      </Tooltip>

      <!-- Options -->
      <ButtonDropdownIcon placement="bottom-end" icon="tabler-dots" size="lg">
        <template #options>
          <ButtonDropdownOption @click="handleEdit" leftIcon="tabler-pencil">
            {{ $t("global.edit") }}
          </ButtonDropdownOption>

          <ButtonDropdownOption
            @click="handleDelete(fontIndex)"
            leftIcon="tabler-trash"
          >
            {{ $t("global.delete") }}
          </ButtonDropdownOption>
        </template>
      </ButtonDropdownIcon>
    </div>

    <!-- Style -->
    <p class="tw:mb-3 tw:text-sm tw:text-secondary-text">
      {{ $t(`brands.settings.typography.styles.${font.style}`) }}
    </p>

    <!-- Category -->
    <div>
      <Chip size="lg">
        {{ $t(`brands.settings.typography.usages.${font.usage}.title`) }}
      </Chip>
    </div>
  </CardBase>
</template>
