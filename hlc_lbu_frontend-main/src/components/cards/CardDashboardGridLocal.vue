<script lang="ts" setup generic="T extends DashboardGridItem">
import { CardGridProps } from "./CardGrid.vue";

export type DashboardGridItem = Record<string, any>;

export type DashboardGridSorter<T> = {
  name: string | keyof T;
  label: string;
  sort: (a: T, b: T) => number;
};

export type DashboardGridSearcher<T> = (
  search: string,
  items: T[],
) => T[] | Promise<T[]>;

interface Props extends CardGridProps {
  itemsIdKey?: keyof T;
  items: T[];
  searchPlaceholder?: string;
  sorters?: DashboardGridSorter<T>[];
  defaultSorter?: string | keyof T;
  searcher?: DashboardGridSearcher<T>;
  pageSize?: number;
}

const props = withDefaults(defineProps<Props>(), { pageSize: 9 });

const searchText = ref("");
const debouncedSearchText = refDebounced(searchText, 500);

const currentSorter = ref<DashboardGridSorter<T> | undefined>(
  props.sorters?.find((sorter) => sorter.name === props.defaultSorter) ??
    undefined,
);
const currentSorterMode = ref<"asc" | "desc" | undefined>("desc");

const handleSetSorter = (sorter: DashboardGridSorter<T>) => {
  if (currentSorter.value?.name != sorter.name) {
    currentSorter.value = sorter;
    currentSorterMode.value = "desc";
  } else {
    if (currentSorterMode.value == "desc") {
      currentSorterMode.value = "asc";
    } else {
      currentSorter.value = undefined;
      currentSorterMode.value = undefined;
    }
  }
};

function sanitizeText(text: string): string {
  return text
    .toLocaleLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

const defaultSearcher: DashboardGridSearcher<T> = (text, items) => {
  text = sanitizeText(text);

  if (text === "") {
    return items;
  }

  return items.filter((item) => {
    const extractedStrings = extractStrings(item);

    return extractedStrings.some((string) =>
      sanitizeText(string).includes(text),
    );
  });
};

const filteredItems = computedAsync(async () => {
  if (props.searcher) {
    return props.searcher(debouncedSearchText.value, props.items);
  }

  return defaultSearcher(debouncedSearchText.value, props.items);
}, props.items);

const sortedItems = computed(() => {
  let items = [...filteredItems.value];

  // Sorting
  if (currentSorter.value) {
    items = items.sort((a, b) => {
      let sort = currentSorter.value?.sort(a, b) ?? 0;

      if (currentSorterMode.value === "desc") {
        sort *= -1;
      }

      return sort;
    });
  }

  return items;
});

//#region Pagination
const parentRef = ref<HTMLDivElement>();
const currentPage = ref(1);
const totalRowCount = computed(() => unref(sortedItems.value).length);
const totalPages = computed(() =>
  Math.ceil(totalRowCount.value / props.pageSize),
);

const startIndex = computed(() => (currentPage.value - 1) * props.pageSize);
const endIndex = computed(() => startIndex.value + props.pageSize);

const paginatedItems = computed(() => {
  const rows = unref(sortedItems.value);
  return rows.slice(startIndex.value, endIndex.value);
});

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
    parentRef.value?.scrollIntoView({ behavior: "instant", block: "start" });
  }
};

const nextPage = () => {
  goToPage(currentPage.value + 1);
};

const previousPage = () => {
  goToPage(currentPage.value - 1);
};

watch(debouncedSearchText, () => {
  currentPage.value = 1;
});
//#endregion
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-4">
    <div
      ref="parentRef"
      class="tw:flex tw:scroll-mt-8 tw:flex-col tw:gap-2"
      :class="{
        'tw:lg:flex-row': !sorters,
        'tw:xl:flex-row': sorters,
      }"
    >
      <div class="tw:flex tw:grow tw:gap-6">
        <FieldBaseText
          v-model="searchText"
          :placeholder="searchPlaceholder ?? $t('global.search')"
          class="tw:w-full tw:lg:basis-[320px]"
          @keydown.enter.prevent
          leftIcon="tabler-search"
        />

        <ButtonDropdown
          v-if="sorters"
          leftIcon="tabler:arrows-sort"
          icon="tabler-chevron-down"
          :color="currentSorter ? 'primary' : 'secondary'"
          variant="label"
          placement="bottom-start"
          class="tw:min-w-max"
          type="button"
        >
          {{ $t("sorter.sort-by") }}

          <template #options>
            <Button
              v-for="sorter in sorters"
              :variant="currentSorter?.name === sorter.name ? 'label' : 'text'"
              :color="
                currentSorter?.name === sorter.name ? 'primary' : 'secondary'
              "
              @click="() => handleSetSorter(sorter)"
              class="tw:justify-between! tw:text-left"
              :icon="
                currentSorter?.name === sorter.name
                  ? currentSorterMode === 'asc'
                    ? 'tabler-chevron-up'
                    : 'tabler-chevron-down'
                  : 'none'
              "
              type="button"
            >
              {{ sorter.label }}
            </Button>
          </template>
        </ButtonDropdown>
      </div>

      <div class="tw:flex tw:flex-col tw:gap-2 tw:xl:flex-row">
        <slot name="actions" />
      </div>
    </div>

    <Separator />

    <div v-if="sortedItems.length === 0">
      <div
        class="tw:mx-auto tw:flex tw:max-w-[350px] tw:flex-col tw:items-center tw:text-center"
      >
        <PageTitle>{{ $t("global.no-results") }}</PageTitle>
        <p>{{ $t("global.no-items-found-try-different-search-term") }}</p>
      </div>
    </div>

    <template v-if="$slots.items || $slots.item">
      <CardGrid :columns="4">
        <template v-if="$slots.item">
          <slot
            v-for="item in paginatedItems"
            :key="itemsIdKey ? item[itemsIdKey] : undefined"
            name="item"
            v-bind="{ ...item }"
          />
        </template>

        <template v-if="$slots.items">
          <slot name="items" v-bind="paginatedItems" />
        </template>
      </CardGrid>
    </template>

    <div
      v-if="totalPages > 1"
      class="tw:mt-4 tw:flex tw:flex-wrap tw:justify-center tw:gap-2"
    >
      <Button
        :disabled="currentPage === 1"
        @click="previousPage"
        icon="tabler-chevrons-left"
        variant="outlined"
        size="md"
        type="button"
      />

      <Button
        v-for="page in totalPages"
        :key="page"
        :variant="currentPage == page ? 'solid' : 'outlined'"
        size="md"
        square
        @click="goToPage(page)"
        type="button"
      >
        {{ page }}
      </Button>

      <Button
        :disabled="currentPage === totalPages"
        @click="nextPage"
        icon="tabler-chevrons-right"
        variant="outlined"
        size="md"
        type="button"
      />
    </div>
  </div>
</template>
