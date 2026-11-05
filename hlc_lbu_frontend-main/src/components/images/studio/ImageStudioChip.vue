<script lang="ts" setup>
import { ImgFileProps } from "@/components/images/ImgFile.vue";

defineProps<{
  src?: ImgFileProps["src"];
}>();

const emit = defineEmits<{ click: []; clickImage: [] }>();

const hasClickImageListener = computed(
  () => !!getCurrentInstance()?.vnode.props?.onClickImage,
);
</script>

<template>
  <div
    class="tw:flex tw:items-center tw:gap-2 tw:rounded-xl tw:bg-primary-100 tw:p-2.5"
  >
    <ImgFile
      v-if="src"
      :src="src"
      class="tw:h-6 tw:rounded tw:object-contain"
      :class="{
        'tw:cursor-pointer': hasClickImageListener,
      }"
      @click="emit('clickImage')"
    />

    <span v-if="$slots.default" class="tw:line-clamp-1 tw:font-medium">
      <slot />
    </span>

    <button type="button" class="tw:h-full tw:py-1" @click="emit('click')">
      <Icon icon="tabler:x" class="tw:text-[14px]" />
    </button>
  </div>
</template>
