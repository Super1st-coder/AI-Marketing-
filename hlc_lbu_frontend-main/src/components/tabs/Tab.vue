<script setup lang="ts">
import { useTabsContext } from "./useTabsContext";

interface Props {
  value: string | number;
  icon?: string;
  /** Extra classes for the `icon`, e.g. to give it a color. */
  iconClass?: ClassName;
  hasAlert?: boolean;
  disableSaveLocking?: boolean;
}

const props = defineProps<Props>();

const tabsContext = useTabsContext();
const { current } = tabsContext ?? {
  current: ref(undefined),
};

const variant = computed(() => tabsContext?.variant.value ?? "default");
const size = computed(() => tabsContext?.size.value ?? "sm");

const isActive = computed(() => current.value === props.value);

async function handleClick() {
  // Ignore if already selected
  if (current.value === props.value) return;

  // Save locking
  if (
    !props.disableSaveLocking &&
    (await useSaveLockingStore().execute()) === "cancel"
  ) {
    return;
  }

  current.value = props.value;
}
</script>

<template>
  <button
    class="tw:flex tw:items-center tw:justify-center tw:gap-2 tw:text-nowrap"
    :class="[
      variant === 'default'
        ? // Default variant
          [
            'tw:border-b-4',
            {
              'tw:px-5 tw:py-2': size === 'sm',
              'tw:h-[72px] tw:px-4 tw:py-6': size === 'lg',
              'tw:border-primary tw:font-bold tw:text-primary': isActive,
              'tw:border-transparent tw:font-medium tw:text-gray-600':
                !isActive,
            },
          ]
        : // Button group variant
          [
            'tw:min-w-[180px] tw:rounded-lg tw:border tw:py-2.5 tw:text-sm tw:font-medium',
            {
              'tw:border-transparent tw:text-gray-500': !isActive,
              'tw:border-gray-300 tw:bg-white': isActive,
            },
          ],
    ]"
    @click="handleClick"
    type="button"
  >
    <Icon v-if="icon" :icon="icon" class="tw:text-xl" :class="iconClass" />

    <slot />

    <Icon
      v-if="hasAlert"
      icon="tabler:alert-triangle"
      class="tw:shrink-0 tw:text-xl tw:text-warning"
    />
  </button>
</template>
