<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalGeneric v-model="isOpen" name="image-studio-improve-results">
    <template #title>{{ $t("image-studio.improve-results.title") }}</template>

    <template #description>
      {{ $t("image-studio.improve-results.description") }}
    </template>

    <ul
      class="tw:list-disc tw:space-y-7 tw:pl-5 tw:font-medium tw:text-gray-700 tw:marker:text-primary"
    >
      <li>
        <i18n-t keypath="image-studio.improve-results.tip-upload-reference">
          <template #uploadToReference>
            <strong>{{ $t("image-studio.upload-to-reference") }}</strong>
          </template>
        </i18n-t>
      </li>

      <li>
        <i18n-t keypath="image-studio.improve-results.tip-photographic-effects">
          <template #photographicEffects>
            <strong>{{ $t("image-studio.add-photographic-effects") }}</strong>
          </template>
        </i18n-t>
      </li>

      <li>
        {{ $t("image-studio.improve-results.tip-prompt-specificity") }}
      </li>
    </ul>

    <template #continue>
      {{ $t("image-studio.improve-results.continue") }}
    </template>
  </ModalGeneric>
</template>
