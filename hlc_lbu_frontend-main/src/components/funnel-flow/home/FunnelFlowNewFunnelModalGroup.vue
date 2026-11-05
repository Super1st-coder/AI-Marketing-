<template>
  <div>
    <h3 class="tw:mb-4 tw:text-xl tw:font-extrabold">
      <slot name="title" />
    </h3>

    <div class="tw:flex tw:flex-col tw:gap-4">
      <slot />
    </div>
  </div>
</template>
