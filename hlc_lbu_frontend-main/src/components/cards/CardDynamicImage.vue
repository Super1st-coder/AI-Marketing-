<script lang="ts" setup>
interface Props {
  isLoading?: MaybeRefOrGetter<boolean>;
  src?: MaybeRefOrGetter<string | undefined | null>;
  loaderSize?: "sm" | "md" | "lg";
  fit?: "cover" | "contain";
}

withDefaults(defineProps<Props>(), { loaderSize: "md", fit: "cover" });
</script>

<template>
  <div class="tw:relative tw:overflow-hidden tw:rounded-xl tw:bg-[#D9D9D9]">
    <div
      v-if="toValue(isLoading)"
      class="flex-center tw:absolute tw:h-full tw:w-full"
    >
      <CircleLoader
        :class="{
          'tw:text-[25px]': loaderSize === 'sm',
          'tw:text-[50px]': loaderSize === 'md',
          'tw:text-[75px]': loaderSize === 'lg',
        }"
      />
    </div>

    <img
      v-if="toValue(src)"
      :src="toValue(src) ?? undefined"
      class="tw:h-full tw:w-full"
      :class="{
        'tw:object-cover': fit === 'cover',
        'tw:object-contain': fit === 'contain',
      }"
    />
  </div>
</template>
