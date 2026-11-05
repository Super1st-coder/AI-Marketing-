<script lang="ts" setup>
defineOptions({
  inheritAttrs: false,
});

export type ImgFileProps = {
  src?: File | Blob | string | null;
};

const props = defineProps<ImgFileProps>();

const fileUrl = useObjectUrl(() =>
  props.src instanceof File || props.src instanceof Blob
    ? props.src
    : undefined,
);

const src = computed(() =>
  typeof props.src === "string" ? props.src : fileUrl.value,
);
</script>

<template>
  <!-- Display image if src is available -->
  <img v-if="src" :src="src" v-bind="$attrs" />
  <!-- Use a div as fallback to avoid broken image icon -->
  <div v-else v-bind="$attrs"></div>
</template>
