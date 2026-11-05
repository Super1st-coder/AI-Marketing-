<script setup lang="ts">
withDefaults(defineProps<{ belowNavbar?: boolean }>(), { belowNavbar: false });
</script>

<template>
  <div class="tw:flex tw:min-h-full tw:flex-col">
    <div
      class="tw:sticky tw:z-20 tw:flex tw:h-[72px] tw:items-center tw:border-b tw:border-gray-300 tw:bg-white"
      :class="{
        'tw:top-[66px]': belowNavbar,
        'tw:top-0': !belowNavbar,
      }"
    >
      <Container
        class="tw:flex tw:items-center tw:justify-between tw:gap-5"
        :maxWidth="1312"
      >
        <!-- Left -->
        <div
          v-if="
            $slots.headerLeft || $slots.headerCenter || $slots.headerBackAction
          "
          class="tw:flex tw:items-center tw:justify-start tw:gap-5"
          :class="{
            'tw:lg:grow tw:lg:basis-0': $slots.headerCenter,
          }"
        >
          <template v-if="$slots.headerBackAction">
            <slot name="headerBackAction" />

            <Separator type="vertical" style="height: 21px" />
          </template>

          <slot name="headerLeft" />
        </div>

        <!-- Center -->
        <div
          v-if="$slots.headerCenter"
          class="tw:flex tw:min-w-0 tw:justify-center tw:lg:grow-2 tw:lg:basis-0"
        >
          <slot name="headerCenter" />
        </div>

        <!-- Right -->
        <div
          v-if="$slots.headerRight || $slots.headerCenter"
          class="tw:flex tw:min-w-0 tw:justify-end"
          :class="{
            'tw:lg:grow tw:lg:basis-0': $slots.headerCenter,
          }"
        >
          <slot name="headerRight" />
        </div>

        <slot name="header" />
      </Container>
    </div>

    <slot v-if="$slots.custom" name="custom" />
    <GradientBackground v-else class="tw:grow">
      <slot />
    </GradientBackground>

    <div
      v-if="$slots.footer"
      class="tw:sticky tw:bottom-0 tw:border-t tw:border-divider tw:bg-white tw:p-6"
    >
      <Container :maxWidth="1312">
        <slot name="footer" />
      </Container>
    </div>
  </div>
</template>
