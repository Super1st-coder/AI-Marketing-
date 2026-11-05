<template>
  <div>
    <span class="tw:text-secondary"> <slot name="label" /> : </span>

    <span class="tw:ml-1 tw:font-semibold">
      <slot name="value" />
    </span>
  </div>
</template>
