<template>
  <div
    class="tw:flex tw:flex-col-reverse tw:justify-between tw:gap-2 tw:border-t tw:border-gray-200 tw:p-4 tw:sm:p-6 tw:md:flex-row"
  >
    <!-- Slot for buttons on the left side  -->
    <div class="tw:flex tw:flex-col-reverse tw:gap-3 tw:md:flex-row">
      <slot name="before" />
    </div>

    <!-- Slot for buttons on the right side. For example: Cancel | Next  -->
    <div class="tw:flex tw:flex-col-reverse tw:gap-3 tw:md:flex-row">
      <slot />
    </div>
  </div>
</template>
