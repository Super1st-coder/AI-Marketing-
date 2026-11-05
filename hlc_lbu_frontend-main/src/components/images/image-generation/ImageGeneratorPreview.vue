<script lang="ts" setup>
import { useField } from "vee-validate";
import { ImageGeneration } from "./ImageGenerator.vue";

const props = defineProps<{ name: string }>();

const { value: field } = useField<ImageGeneration>(() => props.name);

const generatedImageUrl = useObjectOrStringUrl(
  () => field.value?.generatedImage,
);

const slots = useSlots();
const hasSlots = computed(() => slots.before || slots.after);
</script>

<template>
  <div
    :class="[
      'tw:relative tw:flex tw:w-full tw:flex-col tw:px-4 tw:py-5',
      'tw:bg-[#F0EEEE] tw:bg-cover tw:bg-center',
      { 'tw:justify-center': !hasSlots, 'tw:justify-between': hasSlots },
    ]"
    :style="{
      backgroundImage: generatedImageUrl
        ? `url(${generatedImageUrl})`
        : undefined,
    }"
  >
    <slot name="before" />

    <div
      v-if="!field?.generatedImage"
      class="tw:mx-auto tw:flex tw:max-w-[185px] tw:flex-col tw:items-center tw:justify-center"
    >
      <Icon
        icon="ph:rocket-duotone"
        class="tw:mb-3 tw:text-[40px] tw:text-[#65676B]"
      />

      <p
        class="tw:mb-8 tw:text-center tw:text-lg tw:font-medium tw:text-primary-text"
      >
        <template v-if="$slots.default">
          <slot />
        </template>
        <template>
          Generate Image <br />
          Profile with LUCA
        </template>
      </p>

      <Button size="sm" type="button">{{ $t("global.generate") }}</Button>
    </div>

    <slot name="after" />
  </div>
</template>
