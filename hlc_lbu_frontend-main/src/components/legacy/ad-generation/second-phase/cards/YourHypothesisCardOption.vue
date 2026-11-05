<script lang="ts" setup>
import { autoUpdate, useFloating } from "@floating-ui/vue";
import { useField } from "vee-validate";

interface Props {
  index: number;
  name: string;
  options: string[];
}

const props = defineProps<Props>();
const { value, setValue } = useField(() => props.name, undefined);

const reference = ref<HTMLElement>();
const floating = ref<HTMLElement>();
const { floatingStyles } = useFloating(reference, floating, {
  placement: "bottom-start",
  transform: false,
  whileElementsMounted: autoUpdate,
});

const isOpen = ref(false);

onClickOutside(floating, () => {
  if (isOpen.value) {
    isOpen.value = false;
  }
});

const handleSelect = (option: string) => {
  setValue(option);
  isOpen.value = false;
};
</script>

<template>
  <span
    ref="reference"
    class="tw:my-0.5 tw:cursor-pointer tw:rounded tw:px-1 tw:font-semibold"
    :class="{
      'tw:bg-error-light tw:text-error': index === 0,
      'tw:bg-success-light tw:text-success': index === 1,
      'tw:bg-info-light tw:text-info': index === 2,
      'tw:font-extrabold tw:text-[#FF8811]': index === 4,
    }"
    type="button"
    @click="isOpen = !isOpen"
  >
    {{ value }}
  </span>
  <div
    v-show="isOpen"
    ref="floating"
    :style="floatingStyles"
    class="tw:z-10 tw:mt-1 tw:flex tw:flex-col tw:rounded-md tw:bg-white tw:p-2 tw:shadow-md"
  >
    <Button
      v-for="option in options"
      type="button"
      size="sm"
      :variant="value === option ? 'label' : 'text'"
      @click="handleSelect(option)"
      class="tw:text-left!"
    >
      {{ option }}
    </Button>
  </div>
</template>
