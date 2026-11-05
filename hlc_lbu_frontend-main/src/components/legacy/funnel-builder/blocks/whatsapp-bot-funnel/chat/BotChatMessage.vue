<script lang="ts" setup>
interface Props {
  own?: boolean;
}

defineProps<Props>();
</script>

<template>
  <div class="tw:group tw:px-2">
    <div
      class="tw:flex tw:items-start tw:gap-2 tw:border-b-divider tw:py-4 tw:group-not-last:border-b"
      :class="{ 'tw:justify-end': own }"
    >
      <div
        class="tw:shrink-0 tw:rounded-full tw:bg-snackbar tw:p-2.5"
        :class="{ 'tw:order-last': own }"
      >
        <Icon
          v-if="own"
          icon="tabler-user"
          class="tw:text-[28px] tw:text-white"
        />
        <img v-else src="/images/emoji-robot.png" class="tw:h-7 tw:w-7" />
      </div>

      <div class="tw:flex tw:flex-col tw:items-start tw:gap-2">
        <slot />
      </div>
    </div>
  </div>
</template>
