<script lang="ts" setup>
import { FieldBasicProps, FieldLayoutProps } from "./common-field-props";

interface Props
  extends
    Pick<
      FieldBasicProps,
      "name" | "label" | "description" | "required" | "optional" | "error"
    >,
    FieldLayoutProps {}

const props = withDefaults(defineProps<Props>(), {
  orientation: "vertical",
  hideLayout: false,
});
</script>

<template>
  <div
    class="tw:w-full"
    :class="{
      'tw:flex tw:flex-col': !props.hideLayout,
      'tw:lg:flex-row tw:lg:gap-4':
        !props.hideLayout && props.orientation === 'horizontal',
    }"
  >
    <div
      v-if="!props.hideLayout && (label || description || $slots.label)"
      :class="[
        props.orientation === 'horizontal' && 'tw:lg:mt-2',
        props.orientation === 'horizontal' &&
          !props.labelClass &&
          'tw:lg:w-[300px] tw:lg:shrink-0',
        props.labelClass,
        props.optional && 'tw:flex tw:items-start tw:justify-between tw:gap-2',
      ]"
    >
      <FieldLabel :for="name" :required="required">
        <slot name="label">{{ label }}</slot>

        <template v-if="description" #description>{{ description }}</template>

        <template v-if="$slots.labelHelp" #help>
          <slot name="labelHelp" />
        </template>
      </FieldLabel>

      <span
        v-if="props.optional"
        class="tw:mb-1.5 tw:shrink-0 tw:text-xs tw:text-gray-400"
      >
        {{ $t("forms.optional") }}
      </span>
    </div>

    <div
      class="tw:w-full"
      :class="{
        'tw:min-w-0 tw:lg:grow':
          !props.hideLayout && props.orientation === 'horizontal',
      }"
    >
      <slot />

      <FieldError v-if="error">
        {{ error }}
      </FieldError>

      <FieldHint v-if="$slots.hint">
        <slot name="hint" />
      </FieldHint>

      <slot name="after" />
    </div>
  </div>
</template>
