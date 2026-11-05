<script setup lang="ts">
import { RouteLocationRaw, RouterLink } from "vue-router";

export interface BreadcrumbItem {
  /** Visible breadcrumb text. */
  label: string;
  /** Dims the item and blocks clicks. */
  disabled?: boolean;
  /** Vue Router destination. When set, the item renders as a `RouterLink`. */
  to?: RouteLocationRaw;
  /** Click handler. Runs for both links and buttons. */
  onClick?: Function;
}

const props = withDefaults(
  defineProps<{
    data: BreadcrumbItem[];
  }>(),
  {
    data: () => [],
  },
);

function isLast(index: number) {
  return index === props.data.length - 1;
}
</script>

<template>
  <nav :aria-label="$t('global.breadcrumb')">
    <ol
      class="tw:flex tw:w-full tw:list-none tw:flex-wrap tw:items-center tw:gap-3"
    >
      <template v-for="(item, index) in data" :key="item.label">
        <li
          class="tw:flex tw:items-center tw:gap-3"
          :class="{ 'tw:opacity-50': item.disabled }"
        >
          <component
            :is="isLast(index) ? 'span' : item.to ? RouterLink : 'button'"
            :to="item.to"
            class="tw:block tw:text-xs tw:font-medium tw:whitespace-nowrap"
            :class="{
              'tw:text-secondary-text': !isLast(index),
              'tw:cursor-not-allowed!': item.disabled,
              'tw:pointer-events-none': item.disabled,
            }"
            :type="isLast(index) || item.to ? undefined : 'button'"
            :disabled="isLast(index) ? undefined : item.disabled"
            :aria-current="isLast(index) ? 'page' : undefined"
            @click="!isLast(index) && item.onClick?.()"
          >
            {{ item.label }}
          </component>

          <Icon
            v-if="!isLast(index)"
            icon="tabler-chevron-compact-right"
            class="tw:text-xl tw:text-gray-300"
            aria-hidden="true"
          />
        </li>
      </template>
    </ol>
  </nav>
</template>
