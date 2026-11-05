<script setup lang="ts">
const emit = defineEmits<{
  (e: "open-orientation"): void;
  (e: "open-color"): void;
  (e: "open-order-by"): void;
}>();

withDefaults(
  defineProps<{
    orientationLabel?: string;
    colorLabel?: string;
    orderByLabel?: string;
  }>(),
  {
    orientationLabel: ":any",
    colorLabel: ":any",
    orderByLabel: ":any",
  },
);
</script>

<template>
  <div class="tw:flex tw:gap-5">
    <Button
      variant="outlined"
      size="md"
      color="secondary"
      @click="emit('open-orientation')"
    >
      <div class="tw:flex">
        <span class="tw:mr-1">
          {{ $t("image-library.unsplash.orientation") }}
        </span>
        <span class="tw:font-bold">{{ orientationLabel }}</span>
        <Icon icon="tabler-arrow-down" class="tw:ml-1 tw:text-xl" />
      </div>
    </Button>

    <Button
      variant="outlined"
      size="md"
      color="secondary"
      @click="emit('open-color')"
    >
      <div class="tw:flex">
        <span class="tw:mr-1">{{ $t("image-library.unsplash.color") }} </span>
        <span class="tw:font-bold">{{ colorLabel }}</span>
        <Icon icon="tabler-arrow-down" class="tw:ml-1 tw:text-xl" />
      </div>
    </Button>

    <Button
      variant="outlined"
      size="md"
      color="secondary"
      @click="emit('open-order-by')"
    >
      <div class="tw:flex">
        <span class="tw:mr-1"
          >{{ $t("image-library.unsplash.order-by") }}
        </span>
        <span class="tw:font-bold">{{ orderByLabel }}</span>
        <Icon icon="tabler-arrow-down" class="tw:ml-1 tw:text-xl" />
      </div>
    </Button>
  </div>
</template>
