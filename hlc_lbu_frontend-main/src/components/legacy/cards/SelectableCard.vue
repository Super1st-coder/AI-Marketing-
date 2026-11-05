<script lang="ts" setup>
import { computed } from "vue";

interface Props {
  colorSelectedClass?: string;
  variant?: "primary" | "success" | "normal";
}

const props = withDefaults(defineProps<Props>(), {
  colorSelectedClass: "tw:border-transparent tw:bg-primary",
  variant: "primary",
});

const isSelected = defineModel<boolean>("selected");

const selectedClass = computed(() => {
  return isSelected.value ? props.colorSelectedClass : "";
});
</script>

<template>
  <Card
    padding="sm"
    class="tw:border-2"
    :variant="
      isSelected
        ? ['primary', 'success', 'normal'].includes(props.variant!)
          ? props.variant
          : 'normal'
        : 'normal'
    "
  >
    <div class="tw:flex tw:flex-col tw:gap-5">
      <div class="card-header tw:flex tw:items-center tw:gap-5 tw:self-stretch">
        <div class="tw:grow">
          <slot name="header" />
        </div>

        <button
          @click.stop="isSelected = !isSelected"
          type="button"
          class="tw:flex tw:h-[34px] tw:w-[34px] tw:shrink-0 tw:items-center tw:justify-center tw:rounded-[4px] tw:border-2 tw:text-white"
          :class="{
            'tw:border-input-border': !isSelected,
            'tw:border-transparent': isSelected,
            [selectedClass]: isSelected,
          }"
        >
          <Icon v-if="isSelected" icon="tabler-check" class="tw:text-[20px]" />
        </button>
      </div>

      <slot />
    </div>

    <slot name="footer" />
  </Card>
</template>
