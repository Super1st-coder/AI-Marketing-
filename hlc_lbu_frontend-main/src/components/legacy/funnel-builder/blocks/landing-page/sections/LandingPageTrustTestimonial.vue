<template>
  <div class="tw:flex tw:flex-col tw:items-start tw:gap-3">
    <div class="tw:flex tw:gap-1">
      <Icon
        v-for="_star in 5"
        icon="tabler-star-filled"
        class="tw:text-black"
      />
    </div>

    <p class="tw:whitespace-pre-line tw:text-black">
      <slot />
    </p>
  </div>
</template>
