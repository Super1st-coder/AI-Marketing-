<script setup lang="ts" generic="T">
import type { BrandSource } from "@/services/NewBrandsApi";

interface Props {
  isEmpty?: boolean;
  fetcher?: () => Promise<T>;
  aiFetcher?: () => Promise<T>;
  source?: BrandSource[];
}

defineOptions({
  inheritAttrs: false,
});

const props = defineProps<Props>();
const emit = defineEmits<{
  fetched: [value: T];
}>();

const store = useBrandFormStore();

const { t } = useI18n();
const isLoading = ref(false);
const isAiLoading = ref(false);
const displayError = ref(false);

// PDF preview modal state
const isPdfModalOpen = ref(false);
const selectedPageNumber = ref<number | undefined>(undefined);
const selectedPdfBlob = ref<Blob | undefined>();
const selectedPdfBlobUrl = useObjectUrl(() => selectedPdfBlob.value);

// Extract page number from strings like "Page 3", "page 3", "Page3", etc.
const extractPageNumber = (value: string): number | undefined => {
  if (value.toLocaleLowerCase().includes("page ")) {
    const match = value.match(/\d+/);
    return match ? parseInt(match[0], 10) : undefined;
  }

  return undefined;
};

// Filter and map sources to displayable format
const displayableSources = computed(() => {
  if (!props.source || props.source.length === 0) {
    return [];
  }

  // Map sources to a more friendly format
  const sources = props.source.map((source) => {
    if (source.type === "website") {
      return {
        type: "website" as const,
        text: source.value,
        url: source.value,
      };
    }

    if (source.type === "pdf" && source.value) {
      // Check if the blob exists
      const blob: Blob | undefined = store.pdfBlobs[source.value];
      if (!blob) {
        return {
          type: "unknown" as const,
        };
      }

      let page: number | undefined;

      // Extract the page
      if (source.page) {
        if (source.page.includes("-")) {
          // Extract from "page" when value is "1-1" (range)
          const splitted = source.page.split("-");
          const first = splitted[0];

          if (first) {
            // Extract the first number
            const result = parseInt(first, 10);

            if (!isNaN(result)) {
              page = result;
            }
          }
        } else {
          // Extract from "page" when value is "1" (number in a string)
          const result = parseInt(source.page, 10);

          if (!isNaN(result)) {
            page = result;
          }
        }
      } else if (source.value) {
        // Extract from "value" when value is "Page 1"
        page = extractPageNumber(source.value);
      }

      const text = page
        ? t("brands.settings.source.page", { page: page })
        : source.value;

      return {
        type: "pdf" as const,
        text,
        blob,
        page,
      };
    }

    return {
      type: "unknown" as const,
    };
  });

  return sources;
});

// Open PDF modal
const openPdfModal = (blob: Blob, pageNumber: number | undefined) => {
  selectedPdfBlob.value = blob;
  selectedPageNumber.value = pageNumber;
  isPdfModalOpen.value = true;
};

// Handle click research button
const handleClickResearch = async () => {
  if (!props.fetcher) return;

  try {
    displayError.value = false;
    isLoading.value = true;

    const fetchedValue = await props.fetcher();

    if (fetchedValue) {
      emit("fetched", fetchedValue);
    }
  } catch (error) {
    console.error("Error researching online:", error);
    displayError.value = true;
  } finally {
    isLoading.value = false;
  }
};

const handleClickGenerateAi = async () => {
  if (!props.aiFetcher) return;

  try {
    displayError.value = false;
    isAiLoading.value = true;

    const fetchedValue = await props.aiFetcher();

    if (fetchedValue) {
      emit("fetched", fetchedValue);
    }
  } catch (error) {
    console.error("Error generating with AI:", error);
    displayError.value = true;
  } finally {
    isAiLoading.value = false;
  }
};
</script>

<template>
  <!-- Show fill hint when field is empty -->
  <div
    v-if="fetcher && aiFetcher && isEmpty"
    class="tw:flex tw:flex-col tw:gap-2 tw:text-xs"
    v-bind="$attrs"
  >
    <div>
      <i18n-t keypath="brands.settings.identity.research-online.hint">
        <template #researchOnline>
          <Link
            is="button"
            underline
            @click="handleClickResearch"
            :disabled="isLoading || isAiLoading"
          >
            <template v-if="isLoading">
              <CircleLoader class="tw:text-xs" />
            </template>
            <template v-else>
              {{
                $t("brands.settings.identity.research-online.research-online")
              }}
            </template>
          </Link>
        </template>
        <template #generateWithAi>
          <Link
            is="button"
            underline
            @click="handleClickGenerateAi"
            :disabled="isLoading || isAiLoading"
          >
            <template v-if="isAiLoading">
              <CircleLoader class="tw:text-xs" />
            </template>
            <template v-else>
              {{
                $t("brands.settings.identity.research-online.generate-with-ai")
              }}
            </template>
          </Link>
        </template>
      </i18n-t>
    </div>

    <Alert v-if="displayError" type="error">
      {{ $t("brands.settings.identity.research-online.error") }}
    </Alert>
  </div>

  <!-- Show sources -->
  <p
    v-else-if="displayableSources.length > 0"
    class="tw:text-xs tw:text-gray-500"
    v-bind="$attrs"
  >
    <span>{{ $t("brands.settings.source.label") }}</span>
    <template v-for="(sourceItem, index) in displayableSources" :key="index">
      <!-- PDF sources: show as link button that opens modal -->
      <Link
        v-if="sourceItem.type === 'pdf'"
        is="button"
        color="secondary"
        underline
        @click="openPdfModal(sourceItem.blob, sourceItem.page)"
      >
        {{ sourceItem.text }}
      </Link>
      <!-- Website sources: show as external link -->
      <Link
        v-else-if="sourceItem.type === 'website'"
        :href="sourceItem.url"
        external
        color="secondary"
        underline
      >
        {{ sourceItem.text }}
      </Link>
      <span v-if="index < displayableSources.length - 1">, </span>
    </template>
  </p>

  <!-- PDF Preview Modal -->
  <ModalPdfPreview
    v-if="selectedPdfBlobUrl"
    v-model="isPdfModalOpen"
    :pdfUrl="selectedPdfBlobUrl"
    :pageNumber="selectedPageNumber"
  />
</template>
