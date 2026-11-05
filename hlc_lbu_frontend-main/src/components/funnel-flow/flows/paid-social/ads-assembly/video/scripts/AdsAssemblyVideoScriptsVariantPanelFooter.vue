<script setup lang="ts"></script>

<template>
  <div
    class="tw:sticky tw:bottom-0 tw:border-t tw:border-divider tw:bg-white tw:py-6"
  >
    <Container>
      <div class="tw:flex tw:justify-between tw:gap-2">
        <!-- Slot for buttons on the left side  -->
        <div class="tw:flex tw:flex-col-reverse tw:gap-3 tw:md:flex-row">
          <slot name="before" />
        </div>

        <!-- Slot for buttons on the right side. For example: Cancel | Next  -->
        <div class="tw:flex tw:flex-col tw:gap-3 tw:md:flex-row">
          <slot />
        </div>
      </div>
    </Container>
  </div>
</template>
