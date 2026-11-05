<script setup lang="ts">
interface Props {
  pdfUrl: string;
  pageNumber?: number;
}

const props = defineProps<Props>();
const isOpen = defineModel<boolean>({ required: true });

// Computed PDF URL with page fragment
const pdfUrlWithPage = computed(() => {
  if (!props.pdfUrl) return "";

  if (props.pageNumber) {
    return `${props.pdfUrl}#page=${props.pageNumber}`;
  }
  return props.pdfUrl;
});
</script>

<template>
  <Modal v-model="isOpen" :maxWidth="1200" height="90vh" closeButton>
    <div class="tw:h-full tw:w-full tw:overflow-auto tw:p-6 tw:pt-20">
      <object
        :data="pdfUrlWithPage"
        type="application/pdf"
        class="tw:h-full tw:w-full"
      >
        <div class="tw:flex tw:flex-col tw:items-center tw:gap-4 tw:p-8">
          <p class="tw:text-secondary-text">
            {{ $t("modals.pdf-preview.cannot-display") }}
          </p>

          <Button as="a" :href="props.pdfUrl" target="_blank">
            {{ $t("modals.pdf-preview.open-new-tab") }}
          </Button>
        </div>
      </object>
    </div>
  </Modal>
</template>
