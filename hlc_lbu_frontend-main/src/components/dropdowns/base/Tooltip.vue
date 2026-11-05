<script lang="ts" setup>
import { DropdownBaseProps } from "./DropdownBase.vue";

type Props = Omit<DropdownBaseProps, "target"> & {
  disabled?: boolean;
};

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  maxWidth: 300,
});

const target = ref<HTMLDivElement>();
const displayTooltip = ref(false);

watch(
  () => props.disabled,
  (disabled) => {
    if (!disabled) {
      displayTooltip.value = false;
    }
  },
);

const handleMouseEnter = () => {
  if (!props.disabled) {
    displayTooltip.value = true;
  }
};

const handleMouseLeave = () => {
  displayTooltip.value = false;
};
</script>

<template>
  <div
    ref="target"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
    class="tw:inline-block"
  >
    <slot />
  </div>

  <DropdownBase
    v-if="displayTooltip"
    :target="target"
    :placement="placement"
    :maxWidth="maxWidth"
    :variant="variant"
    class="tw:p-2 tw:text-sm"
  >
    <slot name="content" />
  </DropdownBase>
</template>
