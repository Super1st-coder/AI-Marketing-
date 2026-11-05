<script setup lang="ts">
// A ring that spins continuously, with no progress: an arc fading from
// Primary/100 to Primary/500, its end rounded

const props = withDefaults(
  defineProps<{
    diameter?: number;
    thickness?: number;
  }>(),
  { diameter: 140, thickness: 12 },
);

const style = computed(() => ({
  "--spinner-diameter": `${props.diameter}px`,
  "--spinner-thickness": `${props.thickness}px`,
}));
</script>

<template>
  <span class="spinner" :style="style" role="presentation" />
</template>

<style scoped>
.spinner {
  display: inline-block;
  flex-shrink: 0;
  width: var(--spinner-diameter);
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    /* The dot that rounds the end of the arc, at the top */
    radial-gradient(farthest-side, var(--tw-color-primary-500) 94%, #0000) top /
      var(--spinner-thickness) var(--spinner-thickness) no-repeat,
    /* The arc: a quarter empty, then light to dark, ending at the top */
    conic-gradient(
        #0000 25%,
        var(--tw-color-primary-100) 35%,
        var(--tw-color-primary-500)
      );
  /* Keeps only the ring */
  mask: radial-gradient(
    farthest-side,
    #0000 calc(100% - var(--spinner-thickness)),
    #000 calc(100% - var(--spinner-thickness) + 1px)
  );
  animation: spinner-rotate 1.2s infinite linear;
}

@keyframes spinner-rotate {
  100% {
    transform: rotate(1turn);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation-duration: 4s;
  }
}
</style>
