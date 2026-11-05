<script setup lang="ts" generic="T extends unknown">
const props = defineProps<{
  value?: T;
  icon?: string;
  soon?: boolean;
}>();

const model = defineModel<T>();

function handleClick() {
  if (props.soon || props.value === undefined) {
    return;
  }

  model.value = props.value;
}
</script>

<template>
  <CardBase
    :shadow="false"
    :color="soon ? 'secondary' : 'default'"
    :softBackground="soon"
    :outlineColor="!soon && value === model ? 'primary' : undefined"
    :hoverColor="soon ? undefined : 'primary'"
    borderRadius="md"
    class="tw:p-4"
    @click="handleClick"
  >
    <div class="tw:flex tw:items-start tw:gap-3">
      <Icon v-if="icon" :icon="icon" class="tw:shrink-0 tw:text-2xl" />

      <div class="tw:grid tw:grid-cols-1 tw:gap-1">
        <Chip v-if="soon" size="md" class="tw:w-fit">
          {{ $t("global.soon") }}
        </Chip>

        <h3 v-else class="tw:font-bold">
          <slot name="title" />
        </h3>

        <p class="tw:text-sm tw:text-secondary-text">
          <slot name="description" />
        </p>
      </div>
    </div>
  </CardBase>
</template>
