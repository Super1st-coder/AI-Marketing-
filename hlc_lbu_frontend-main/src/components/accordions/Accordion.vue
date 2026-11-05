<script setup lang="ts">
import { IconCardVariant } from "../cards/IconCard.vue";
import { AccordionVariant, useAccordionContext } from "./useAccordionContext";

export interface AccordionProps {
  title?: string;
  description?: string;
  icon?: string;
  variant?: AccordionVariant;
  iconVariant?: IconCardVariant;
  color?: "default" | "error";
  titleClass?: string;
  openByDefault?: boolean;
  disabled?: boolean;
  openOnUnDisabled?: boolean;
  noContentPadding?: boolean;
  hideChevron?: boolean;
  shrinkActions?: boolean;
}

const props = withDefaults(defineProps<AccordionProps>(), {
  color: "default",
  disabled: false,
  openOnUnDisabled: false,
  noContentPadding: false,
  hideChevron: false,
  shrinkActions: false,
});

const accordionContext = useAccordionContext();
const variant = computed(() => props.variant ?? accordionContext.variant.value);

const isOpen = defineModel<boolean>({
  default: false,
});

const headerId = useId();
const panelId = useId();

function isFromHeaderEnd(event: Event) {
  const target = event.target;
  if (!(target instanceof Element)) {
    return false;
  }

  return Boolean(target.closest("[data-accordion-header-end]"));
}

function handleHeaderClick(event: MouseEvent | KeyboardEvent) {
  if (props.hideChevron || props.disabled || isFromHeaderEnd(event)) {
    return;
  }

  isOpen.value = !isOpen.value;
}

// Open accordion by default
onMounted(() => {
  if (props.openByDefault) {
    isOpen.value = true;
  }
});

// Close accordion if disabled
watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) {
      isOpen.value = false;
    } else {
      if (props.openOnUnDisabled) {
        isOpen.value = true;
      }
    }
  },
);
</script>

<template>
  <div
    class="tw:@container tw:flex tw:flex-col"
    :class="{
      'tw:overflow-hidden': noContentPadding,

      // Background
      'tw:bg-white':
        (color === 'default' || color === 'error') && variant !== 'text',

      // Border
      'tw:border tw:border-error': color === 'error' && variant !== 'text',
      'tw:border tw:border-gray-200': variant === 'card',

      // Shadow
      'tw:rounded-lg tw:shadow-[0_1px_6px_#2F2B3D1A]': variant === 'default',
      'tw:rounded-2xl tw:shadow-[0_2px_12px] tw:shadow-gray-900/3':
        variant === 'card',

      // Disabled
      'tw:opacity-50': disabled,
    }"
  >
    <!-- Header -->
    <div
      class="tw:flex tw:gap-2"
      :class="{
        'tw:px-6 tw:py-6': variant === 'card',
        'tw:py-3': variant === 'text',
        'tw:px-6 tw:py-3': variant !== 'card' && variant !== 'text',
        'tw:cursor-pointer': !hideChevron,
        'tw:cursor-default': hideChevron,
        'tw:items-start tw:@2xl:items-center': $slots.actions,
        'tw:items-center': !$slots.actions,
      }"
      @click="handleHeaderClick"
    >
      <!-- Icon -->
      <slot name="icon">
        <IconCard v-if="icon" :icon="icon" :variant="iconVariant" size="sm" />
      </slot>

      <!-- Content. Can shrink, so a truncated title doesn't push the chevron out -->
      <div
        class="tw:flex tw:min-w-0 tw:grow tw:flex-col tw:gap-2 tw:text-left tw:@2xl:flex-row tw:@2xl:items-center"
      >
        <!-- Header title and description -->
        <div class="tw:min-w-0 tw:grow">
          <!-- Title -->
          <h3
            class="tw:text-left"
            :class="[
              {
                'tw:text-primary tw:underline': variant === 'text',
              },
              $props.titleClass ?? 'tw:text-lg tw:font-medium',
            ]"
          >
            <!-- Button when the chevron is visible -->
            <button
              v-if="!hideChevron"
              :id="headerId"
              type="button"
              class="tw:flex tw:w-full tw:items-center tw:gap-2.5 tw:text-left"
              :aria-expanded="isOpen"
              :aria-controls="panelId"
              :disabled="disabled"
            >
              <slot name="title">
                {{ title }}
              </slot>
            </button>
            <!-- When the chevron is not visible -->
            <span v-else class="tw:flex tw:items-center tw:gap-2.5">
              <slot name="title">
                {{ title }}
              </slot>
            </span>
          </h3>

          <!-- Custom title -->
          <slot name="customTitle" />

          <!-- Description -->
          <span
            v-if="description || $slots.description"
            class="tw:text-sm tw:text-secondary-text"
          >
            <slot name="description">
              {{ description }}
            </slot>
          </span>
        </div>

        <!-- Actions -->
        <div
          v-if="$slots.actions"
          :class="shrinkActions ? 'tw:min-w-0' : 'tw:shrink-0'"
          data-accordion-header-end
        >
          <slot name="actions" />
        </div>
      </div>

      <!-- Header end -->
      <div
        v-if="$slots.headerEnd"
        class="tw:shrink-0"
        data-accordion-header-end
      >
        <slot name="headerEnd" />
      </div>

      <!-- Chevron -->
      <Icon
        v-if="!hideChevron"
        :icon="isOpen ? 'tabler-chevron-down' : 'tabler-chevron-right'"
        class="tw:shrink-0 tw:text-xl"
        aria-hidden="true"
      />
    </div>

    <!-- Content -->
    <div
      :id="panelId"
      v-show="isOpen"
      :role="hideChevron ? undefined : 'region'"
      :aria-labelledby="hideChevron ? undefined : headerId"
      :class="{
        'tw:pb-5': !noContentPadding,
        'tw:px-6': !noContentPadding && variant !== 'text',
      }"
    >
      <Separator
        v-if="variant === 'card'"
        :class="{ 'tw:mb-3': !noContentPadding }"
      />

      <slot />
    </div>

    <!-- Footer -->
    <div
      v-if="$slots.footer"
      :class="{
        'tw:pb-6': variant === 'card',
        'tw:pb-3': variant !== 'card',

        'tw:px-6': variant !== 'text',
        'tw:pt-3': noContentPadding && isOpen,
      }"
    >
      <slot name="footer" />
    </div>
  </div>
</template>
