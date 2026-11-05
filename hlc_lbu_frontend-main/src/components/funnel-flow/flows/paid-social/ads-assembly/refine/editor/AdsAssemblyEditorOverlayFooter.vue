<script setup lang="ts"></script>

<template>
  <div
    class="tw:sticky tw:bottom-0 tw:border-t tw:border-divider tw:bg-white tw:py-6"
  >
    <Container :maxWidth="1312">
      <div class="tw:flex tw:flex-col tw:justify-end tw:gap-3 tw:lg:flex-row">
        <slot />
      </div>
    </Container>
  </div>
</template>
