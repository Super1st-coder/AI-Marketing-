<script lang="ts" setup>
import { RouteLocationRaw, RouterLink } from "vue-router";
import clsx from "clsx";

export type SidebarLinkColor = "normal" | "primary" | "success" | "link";

export interface SidebarLinkRingLoader {
  steps: number;
  completedSteps: number;
}

export interface SidebarLinkProps {
  to?: RouteLocationRaw;
  replace?: boolean;
  icon?: string;
  hasAlert?: boolean;
  hasSuccess?: boolean;
  disabled?: boolean;
  variant?: SidebarLinkColor;
  selected?: boolean;
  /** When false, also highlight for nested/child routes (router-link-active). */
  exact?: boolean;
  expandable?: boolean;
  ringLoader?: SidebarLinkRingLoader;
}

const props = withDefaults(defineProps<SidebarLinkProps>(), {
  variant: "normal",
  expandable: true,
  exact: true,
});

const store = useMenusStore();

const _variant = computed<SidebarLinkColor>(() =>
  props.hasSuccess ? "success" : props.variant,
);

const activeClasses = computed(() =>
  props.to
    ? clsx([
        "tw:rounded-xl tw:border tw:border-primary-200 tw:bg-primary-100 tw:text-primary!",
        {
          "tw:text-gray-400": _variant.value === "normal",
          "tw:text-success": _variant.value === "success",
          "tw:text-primary": _variant.value === "link",
        },
      ])
    : undefined,
);
</script>

<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to"
    :replace="replace"
    class="tw:flex tw:w-full tw:items-center tw:gap-3 tw:p-3 tw:text-left tw:text-pretty tw:disabled:opacity-50"
    :class="{
      'tw:rounded-xl tw:border tw:border-primary-200 tw:bg-primary-100 tw:text-primary!':
        selected,

      // Icon color
      'tw:text-gray-400': _variant === 'normal',
      'tw:text-primary': _variant === 'primary' || _variant === 'link',
      'tw:text-success': _variant === 'success',

      // Disabled
      'tw:cursor-pointer': !disabled,
      'tw:pointer-events-none tw:opacity-40': disabled,
    }"
    :activeClass="to && !exact ? activeClasses : undefined"
    :exactActiveClass="to && exact ? activeClasses : undefined"
    :disabled="disabled"
  >
    <ProgressRing
      v-if="ringLoader"
      color="success"
      :diameter="20"
      :thickness="3"
      :progress="ringLoader.completedSteps / ringLoader.steps"
    />

    <!-- Left Icon -->
    <Icon
      v-if="icon && !ringLoader"
      :icon="icon"
      class="tw:inline tw:shrink-0 tw:text-xl tw:md:text-lg tw:lg:text-xl"
      :class="{
        'tw:text-success': _variant === 'success',
        'tw:text-primary': _variant === 'link',
      }"
    />

    <!-- Text -->
    <span
      v-if="store.isMenuVisuallyExpanded || !expandable"
      class="tw:grow tw:text-base tw:leading-none! tw:md:text-sm tw:lg:text-base"
      :class="{
        'tw:font-semibold': ringLoader,
        'tw:font-medium': !ringLoader,
        'tw:text-gray-900': _variant === 'normal',
        'tw:text-success': _variant === 'success',
        'tw:text-primary tw:underline tw:underline-offset-2':
          _variant === 'link',
      }"
    >
      <slot />

      <span v-if="ringLoader" class="tw:font-medium tw:text-gray-500">
        {{
          $t("global.steps-progress", {
            completed: ringLoader.completedSteps,
            total: ringLoader.steps,
          })
        }}
      </span>
    </span>

    <!-- Alert Icon -->
    <Icon
      v-if="hasAlert"
      icon="tabler:alert-triangle"
      class="tw:ml-auto tw:inline tw:shrink-0 tw:text-xl tw:text-warning tw:md:text-lg tw:lg:text-xl"
    />

    <!-- Success Icon -->
    <Icon
      v-if="hasSuccess"
      icon="tabler-circle-check-filled"
      class="tw:ml-auto tw:inline tw:shrink-0 tw:text-xl tw:text-success tw:md:text-lg tw:lg:text-xl"
    />

    <slot name="after" />
  </component>
</template>
