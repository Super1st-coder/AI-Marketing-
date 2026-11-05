<script lang="ts" setup>
interface Props {
  required?: boolean;
  for?: string;
}

const props = defineProps<Props>();
</script>

<template>
  <label
    :for="props.for"
    class="tw:mb-1.5 tw:inline-block tw:text-sm tw:font-semibold tw:text-pretty tw:text-gray-700"
  >
    <slot /><template v-if="required">*</template>

    <Tooltip v-if="$slots.help" :maxWidth="400" placement="right">
      <Icon
        icon="tabler-help-circle"
        class="tw:ml-1 tw:inline-block tw:text-2xl tw:text-primary"
      />

      <template #content>
        <slot name="help" />
      </template>
    </Tooltip>
    <slot name="after" />

    <template v-if="$slots.description">
      <br />
      <span class="tw:font-normal tw:text-secondary-text">
        <slot name="description" />
      </span>
    </template>
  </label>
</template>
