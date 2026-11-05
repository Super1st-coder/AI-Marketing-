<script setup lang="ts">
import { computed } from "vue";

interface Props {
  src?: string;
  alt?: string;
}

const props = defineProps<Props>();

const isPdf = computed(() => (props.src ? isUrlAPdf(props.src) : false));
</script>

<template>
  <object v-if="isPdf" :data="src" type="application/pdf">
    <p>
      PDF cannot be displayed.
      <a :href="src" target="_blank" rel="noopener noreferrer">
        Open PDF in new tab
      </a>
    </p>
  </object>
  <img v-else :src="src" :alt="alt" />
</template>
