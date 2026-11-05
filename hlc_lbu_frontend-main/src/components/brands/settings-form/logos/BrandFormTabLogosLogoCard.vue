<script setup lang="ts">
import type { BrandFormLogo } from "../BrandFormTabLogos.vue";
import { brandFormLogoCategories } from "@/services/NewBrandsApi";

interface Props {
  logo: BrandFormLogo;
}

const props = defineProps<Props>();
const { t } = useI18n();

const hasValidCategory = computed(() =>
  brandFormLogoCategories.includes(props.logo.category),
);
const hasDescription = computed(() => !!props.logo.description?.trim());
const hasAliasForCustomLogo = computed(
  () => props.logo.category !== "custom" || !!props.logo.category_alias?.trim(),
);

const isCompleted = computed(
  () =>
    hasValidCategory.value &&
    !!props.logo.image &&
    hasDescription.value &&
    hasAliasForCustomLogo.value,
);

const supportedFormatsText = computed(() =>
  BRAND_LOGO_ACCEPTED_FORMATS.map((format) =>
    t(`forms.file-upload.formats.${format}`),
  ).join(", "),
);

const maxLogoSizeText = computed(() =>
  formatFileSize(BRAND_LOGO_MAX_FILE_SIZE_BYTES),
);

const emit = defineEmits<{
  edit: [logo: BrandFormLogo];
  delete: [logo: BrandFormLogo];
}>();

const handleEdit = () => {
  emit("edit", props.logo);
};

const handleDelete = () => {
  emit("delete", props.logo);
};
</script>

<template>
  <CardBase class="tw:p-4" borderRadius="md">
    <!-- Logo Preview/Placeholder -->
    <CardBase
      class="tw:mb-3 tw:aspect-313/170 tw:overflow-hidden"
      color="secondary"
      borderRadius="sm"
    >
      <!-- Filled State -->
      <ImgFile
        v-if="logo.image"
        :src="logo.image"
        class="tw:h-full tw:w-full tw:object-contain"
      />
    </CardBase>

    <!-- Header -->
    <div class="tw:mb-2.5 tw:flex tw:items-center tw:gap-3.5">
      <!-- Category -->
      <h3 class="tw:grow tw:text-lg tw:font-bold">
        {{
          logo.category === "custom" && logo.category_alias
            ? logo.category_alias
            : $t(`brands.settings.logos.categories.${logo.category}.title`)
        }}
      </h3>

      <!-- Warning -->
      <Tooltip v-if="!isCompleted" placement="top" :maxWidth="213">
        <Icon
          icon="tabler:alert-triangle"
          class="tw:text-2xl tw:text-warning"
        />

        <template #content>
          {{
            !hasValidCategory
              ? $t("brands.settings.logos.warnings.invalid-category")
              : !hasAliasForCustomLogo
                ? $t("brands.settings.logos.warnings.missing-alias")
                : !hasDescription
                  ? $t("brands.settings.logos.warnings.missing-description")
                  : $t("brands.settings.logos.warnings.incomplete", {
                      formats: supportedFormatsText,
                      maxSize: maxLogoSizeText,
                    })
          }}
        </template>
      </Tooltip>

      <!-- Options -->
      <ButtonDropdownIcon placement="bottom-end" icon="tabler-dots" size="lg">
        <template #options>
          <ButtonDropdownOption @click="handleEdit" icon="tabler-pencil">
            {{ $t("global.edit") }}
          </ButtonDropdownOption>

          <ButtonDropdownOption @click="handleDelete" icon="tabler-trash">
            {{ $t("global.delete") }}
          </ButtonDropdownOption>
        </template>
      </ButtonDropdownIcon>
    </div>

    <!-- Description -->
    <p class="tw:text-sm tw:text-gray-500">
      {{ logo.description }}
    </p>

    <!-- Source -->
    <BrandFormSourceHint :source="logo.source" class="tw:mt-3" />
  </CardBase>
</template>
