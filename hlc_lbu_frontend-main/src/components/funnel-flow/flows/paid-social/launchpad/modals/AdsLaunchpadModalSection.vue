<template>
  <div class="tw:mb-6">
    <!-- Header -->
    <div class="tw:mb-5 tw:flex tw:items-center tw:justify-between">
      <h3 class="tw:text-sm">
        <slot name="title" />
      </h3>

      <slot name="actions" />
    </div>

    <!-- Videos -->
    <div>
      <slot />
    </div>
  </div>
</template>
