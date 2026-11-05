<template>
  <div
    class="tw:mb-2.5"
    :class="{
      'tw:flex tw:items-start tw:gap-5': $slots.button,
    }"
  >
    <h1
      class="tw:font-public-sans tw:text-2xl tw:leading-relaxed tw:font-extrabold tw:text-primary-text tw:lg:text-[38px]"
    >
      <slot />
    </h1>

    <slot name="button" />
  </div>
</template>
