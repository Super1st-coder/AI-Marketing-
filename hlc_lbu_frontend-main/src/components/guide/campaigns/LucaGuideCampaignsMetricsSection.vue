<template>
  <section class="tw:flex tw:flex-col tw:gap-3">
    <div
      v-if="$slots.title || $slots.titleAfter"
      class="tw:flex tw:flex-wrap tw:items-center tw:gap-2"
    >
      <h2
        v-if="$slots.title"
        class="tw:text-sm tw:text-secondary-text tw:uppercase"
      >
        <slot name="title" />
      </h2>

      <slot name="titleAfter" />
    </div>

    <div v-if="$slots.alert">
      <slot name="alert" />
    </div>

    <slot />
  </section>
</template>
