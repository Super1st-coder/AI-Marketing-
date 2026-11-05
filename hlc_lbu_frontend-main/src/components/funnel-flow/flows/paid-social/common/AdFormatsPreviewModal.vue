<script setup lang="ts">
import { AdMediaFormat } from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{
  adSetName: string;
  adName: string;
  formats: AdMediaFormat[];
}>();

const isOpen = defineModel<boolean>({ required: true });

const currentFormatId = ref<string | undefined>(undefined);
const selectedFormat = computed(() =>
  props.formats.find((format) => format.id === currentFormatId.value),
);

watch(
  () => props.formats,
  (newFormats) => {
    if (newFormats.length > 0) {
      currentFormatId.value = newFormats[0].id;
    } else {
      currentFormatId.value = "";
    }
  },
  { immediate: true },
);
</script>

<template>
  <Modal v-model="isOpen" closeButton alignment="top" :maxWidth="1054">
    <div class="tw:grid tw:grid-cols-8">
      <div class="tw:col-span-2 tw:border-r tw:border-r-divider tw:p-5">
        <div
          class="tw:-mx-5 tw:mb-5 tw:flex tw:h-12 tw:items-center tw:border-b tw:border-b-divider tw:px-5"
        >
          <h3 class="tw:text-2xl tw:font-bold">
            {{ $t("global.formats") }}
          </h3>
        </div>
        <ul>
          <li
            class="tw:mb-3 tw:flex tw:cursor-pointer tw:items-center tw:gap-5 tw:rounded-md tw:bg-secondary/10 tw:p-3"
            :class="{
              'tw:border tw:border-primary': currentFormatId === format.id,
            }"
            v-for="format in props.formats"
            :key="format.id"
            @click="currentFormatId = format.id"
          >
            <ImgAndPdf
              class="tw:h-auto tw:w-10"
              :src="format?.visual_url ?? format.preview_url ?? undefined"
              alt=""
            />
            <span> {{ format.width }} x {{ format.height }} </span>
          </li>
        </ul>
      </div>

      <div class="tw:col-span-6 tw:p-5">
        <div
          class="tw:-mx-5 tw:mb-5 tw:flex tw:h-12 tw:items-center tw:border-b tw:border-b-divider tw:px-5"
        >
          <span class="tw:text-base">
            <span class="tw:text-secondary/50">
              {{ props.adSetName }} > {{ props.adName }} >
            </span>
            <span class="tw:font-bold">
              {{ selectedFormat?.width }} x
              {{ selectedFormat?.height }}
            </span>
          </span>
        </div>
        <div class="tw:flex tw:h-full tw:items-center tw:justify-center tw:p-5">
          <div
            class="tw:w-1/2 tw:rounded-xl tw:border tw:border-secondary/40 tw:p-5 tw:shadow-lg"
          >
            <div class="tw:mb-5 tw:text-center">
              <h4 class="tw:text-2xl tw:font-bold">{{ selectedFormat?.id }}</h4>
              <div>
                {{ selectedFormat?.width }} x {{ selectedFormat?.height }} px
              </div>
            </div>
            <ImgAndPdf
              :src="
                selectedFormat?.visual_url ??
                selectedFormat?.preview_url ??
                undefined
              "
              class="tw:rounded-xl tw:border-2 tw:border-dashed"
            />
          </div>
        </div>
      </div>
    </div>
  </Modal>
</template>
