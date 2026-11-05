<script setup lang="ts">
import { AdSetData } from "@/services/funnel-flow/paid-social/AdStructureApi";

// Extiende el tipo de ad para permitir AdshasAlert
type AdWithAlert = { id: number; name: string; hasAlert?: boolean };

export type AdSetSidebar = Omit<AdSetData, "ads"> & {
  open?: boolean;
  hasAlert?: boolean;
  ads: AdWithAlert[];
};

const props = withDefaults(
  defineProps<{
    title: string;
    adSets?: AdSetSidebar[];
    adSetsClickeables?: boolean;
    adsClickeables?: boolean;
    mode?: "set" | "ad";
  }>(),
  {
    name: "",
    adSets: () => [],
    adSetsClickeables: true,
    adsClickeables: true,
    mode: "set",
  },
);

const emit = defineEmits<{
  selectAdSet: [adSetId: number, adSetIndex: number];
  selectAd: [
    adSetId: number,
    adId: number,
    adSetIndex: number,
    adIndex: number,
  ];
}>();

const localSets = ref<AdSetSidebar[]>(
  props.adSets.map((s) => ({ ...s, open: true })),
);

const initialAdSet = localSets.value[0];
const selectedAdSetId = ref<number>(initialAdSet.id);
const selectedAdSetIndex = computed(() =>
  localSets.value.findIndex((set) => set.id === selectedAdSetId.value),
);

const selectedAdId = ref<number | undefined>(
  props.mode === "ad" ? initialAdSet.ads[0].id : undefined,
);

function selectAdSetByIndex(adSetIndex: number, adId?: number) {
  if (adSetIndex < 0 || adSetIndex >= localSets.value.length) return;

  const next = localSets.value[adSetIndex];

  if (selectedAdSetId.value === next.id || !next.open) {
    localSets.value[adSetIndex].open = !next.open;
  }

  selectedAdSetId.value = next.id;
  selectedAdId.value = adId;

  emit("selectAdSet", next.id, adSetIndex);
}

function goNext(wrap = false) {
  if (!localSets.value.length) return;
  const currentIndex = selectedAdSetIndex.value;
  const lastIndex = localSets.value.length - 1;

  if (currentIndex === lastIndex && !wrap) return;

  const nextIndex = currentIndex === lastIndex ? 0 : currentIndex + 1;

  selectAdSetByIndex(nextIndex);
}

function goPrev(wrap = false) {
  if (!localSets.value.length) return;

  const currentIndex = selectedAdSetIndex.value;

  if (currentIndex === 0 && !wrap) return;

  const previousIndex =
    currentIndex === 0 ? localSets.value.length - 1 : currentIndex - 1;
  selectAdSetByIndex(previousIndex);
}

function goToAdSetId(adSetId: number) {
  const index = localSets.value.findIndex((s) => s.id === adSetId);
  if (index !== -1) selectAdSetByIndex(index);
}

function goToAdId(adId: number) {
  const adSetIndex = localSets.value.findIndex((set) =>
    set.ads.some((ad) => ad.id === adId),
  );
  if (adSetIndex === -1) return;

  const adIndex = localSets.value[adSetIndex].ads.findIndex(
    (ad) => ad.id === adId,
  );
  if (adIndex === -1) return;

  selectAdSetByIndex(adSetIndex, adId);
}

watch(
  () => props.adSets,
  (val) => {
    localSets.value = val.map((s) => ({ ...s }));

    if (
      selectedAdSetId.value == null ||
      !localSets.value.some((s) => s.id === selectedAdSetId.value)
    ) {
      selectedAdSetId.value = localSets.value[0]?.id ?? null;
    }
  },
  { deep: true },
);

const toggleSet = (index: number) => {
  if (props.adSetsClickeables) {
    selectAdSetByIndex(index);
  }
};

const selectAd = async (
  adSetId: number,
  adId: number,
  adSetIndex: number,
  adIndex: number,
) => {
  if (props.adsClickeables) {
    // Save locking
    if ((await useSaveLockingStore().execute()) === "cancel") return;

    emit("selectAd", adSetId, adId, adSetIndex, adIndex);
  }
};

defineExpose({
  goNext,
  goPrev,
  goToAdSetId,
  goToAdId,
  getSelectedAdSetId: () => selectedAdSetId.value,
  getOpenIndex: () => selectedAdSetIndex.value,
});
</script>

<template>
  <div class="tw:grid tw:w-full tw:grid-cols-12">
    <div
      class="tw:col-span-12 tw:border-r tw:border-r-divider tw:bg-white tw:md:col-span-5 tw:lg:col-span-4 tw:xl:col-span-3 tw:2xl:col-span-2"
    >
      <h3 class="tw:p-4 tw:font-bold">{{ props.title }}</h3>

      <div v-for="(set, idx) in localSets" :key="set.id">
        <h3
          class="tw:flex tw:items-center tw:p-3 tw:font-bold tw:select-none"
          :class="{
            'tw:bg-primary/30':
              props.adSetsClickeables && set.id === selectedAdSetId,
            'tw:cursor-pointer tw:hover:bg-primary/30': props.adSetsClickeables,
          }"
          @click="toggleSet(idx)"
        >
          <Icon icon="mingcute-grid-2-line" class="tw:mr-2 tw:text-2xl" />
          <span class="tw:flex-1">{{ set.name }}</span>
          <Icon
            v-if="set.hasAlert"
            icon="tabler:alert-triangle"
            class="tw:mr-3 tw:text-2xl tw:text-primary"
          />
          <Icon
            :icon="set.open ? 'tabler-chevron-down' : 'tabler-chevron-right'"
            class="tw:text-lg"
            v-if="props.adSetsClickeables"
          />
        </h3>

        <ul v-show="set.open || adsClickeables" class="animate-fadeIn">
          <li
            v-for="(ad, adIdx) in set.ads"
            :key="ad.id"
            @click="selectAd(set.id, ad.id, idx, adIdx)"
            class="tw:flex tw:items-center tw:p-3 tw:text-secondary/40"
            :class="{
              'tw:cursor-pointer tw:hover:bg-secondary/10':
                props.adsClickeables,
              'tw:bg-primary/20': selectedAdId === ad.id,
            }"
          >
            <Icon icon="proicons-window" class="tw:mr-2 tw:text-2xl" />
            <span class="tw:flex-1">{{ ad.name }}</span>
            <Icon
              v-if="ad.hasAlert === true"
              icon="tabler:alert-triangle"
              class="tw:ml-2 tw:text-2xl tw:text-primary"
            />
          </li>
        </ul>
      </div>
    </div>

    <div
      class="tw:col-span-12 tw:md:col-span-7 tw:lg:col-span-8 tw:xl:col-span-9 tw:2xl:col-span-10"
    >
      <slot />
    </div>
  </div>
</template>

<style>
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
.animate-fadeIn {
  animation: fadeIn 0.3s ease-in-out;
}
</style>
