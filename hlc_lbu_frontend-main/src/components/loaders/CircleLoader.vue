<template>
  <span class="tw:inline-flex">
    <span class="loader"></span>
  </span>
</template>

<style scoped>
.loader {
  width: 1em;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(farthest-side, currentColor 80%, #0000) top/0.25em 0.25em
      no-repeat,
    conic-gradient(#0000 30%, currentColor);
  mask: radial-gradient(farthest-side, #0000 calc(100% - 0.25em), #000 0);
  animation: l13 1s infinite linear;
}

@keyframes l13 {
  100% {
    transform: rotate(1turn);
  }
}
</style>
