<script lang="ts" setup generic="T extends DashboardGridItem">
import { CardGridProps } from "./CardGrid.vue";

export type DashboardGridItem = Record<string, any>;

export type DashboardGridSorterKey = string;

export type DashboardGridSorter = {
  key: DashboardGridSorterKey;
  label: string;
};

export type DashboardGridLoadOptions = {
  itemsLength: number;
  paginationOptions: ApiDefaultPaginationOptions;
  scrollToTop?: () => void;
};

interface Props extends CardGridProps {
  itemsIdKey?: keyof T;
  items: T[];
  searchPlaceholder?: string;
  sorters?: DashboardGridSorter[];
  defaultSorter?: DashboardGridSorterKey;
  itemsLength: number;
  itemsPerPage: number;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  itemsLength: 9,
  defaultSorter: "updatedAt",
});
const emit = defineEmits<{
  update: [options: DashboardGridLoadOptions];
}>();

const searchText = defineModel<string | undefined>("searchText", {
  required: false,
  default: undefined,
});
const debouncedSearchText = refDebounced(searchText, 500);

//#region Sorting
const currentSorterKey = ref<string | undefined>(props.defaultSorter);
const currentSorterMode = ref<"asc" | "desc" | undefined>("desc");

const handleSetSorter = (sorter: DashboardGridSorter) => {
  if (currentSorterKey.value != sorter.key) {
    currentSorterKey.value = sorter.key;
    currentSorterMode.value = "desc";
  } else {
    if (currentSorterMode.value == "desc") {
      currentSorterMode.value = "asc";
    } else {
      currentSorterKey.value = undefined;
      currentSorterMode.value = undefined;
    }
  }
};
//#endregion

//#region Pagination
const parentRef = ref<HTMLDivElement>();
const currentPage = ref(1);
const totalPages = computed(() =>
  Math.ceil(props.itemsLength / props.itemsPerPage),
);

const scrollToTop = () => {
  parentRef.value?.scrollIntoView({ behavior: "instant", block: "nearest" });
};

const update = () => {
  const start = (currentPage.value - 1) * props.itemsPerPage;
  const end = currentPage.value * props.itemsPerPage - 1;

  // Emit update event
  emit("update", {
    itemsLength: props.itemsLength,
    paginationOptions: {
      range: [start, end],
      order:
        currentSorterKey.value && currentSorterMode.value
          ? {
              [currentSorterKey.value]: currentSorterMode.value,
            }
          : undefined,
      filter: { name: debouncedSearchText.value },
    },
    scrollToTop,
  });
};

const firstPage = () => {
  currentPage.value = 1;
};

const lastPage = () => {
  currentPage.value = totalPages.value;
};

const nextPage = () => {
  currentPage.value = currentPage.value + 1;
};

const previousPage = () => {
  currentPage.value = currentPage.value - 1;
};

// Reset page to 1 when the search or the sorting are changed
watch([debouncedSearchText, currentSorterKey], () => {
  currentPage.value = 1;
});

// Update items
watch(
  [debouncedSearchText, currentPage, currentSorterKey, currentSorterMode],
  () => {
    update();
  },
);
//#endregion
</script>

<template>
  <div
    class="tw:flex tw:flex-col tw:gap-8"
    :class="{ 'tw:opacity-50': loading }"
  >
    <!-- Header -->
    <div
      ref="parentRef"
      class="tw:flex tw:scroll-mt-8 tw:flex-col tw:gap-3 tw:lg:flex-row"
    >
      <div class="tw:flex tw:grow tw:flex-col tw:gap-3 tw:sm:flex-row">
        <!-- Search input -->
        <FieldBaseText
          v-model.trim="searchText"
          :placeholder="searchPlaceholder ?? $t('global.search')"
          class="tw:w-full tw:lg:basis-[320px]"
          @keydown.enter.prevent
          leftIcon="tabler-search"
        />

        <!-- Sorting dropdown -->
        <ButtonDropdown
          v-if="sorters"
          leftIcon="tabler:arrows-sort"
          icon="tabler-chevron-down"
          :color="currentSorterKey ? 'primary' : 'secondary'"
          variant="label"
          placement="bottom-start"
          class="tw:min-w-max"
          type="button"
        >
          {{ $t("sorter.sort-by") }}

          <template #options>
            <Button
              v-for="sorter in sorters"
              :variant="currentSorterKey === sorter.key ? 'label' : 'text'"
              :color="currentSorterKey === sorter.key ? 'primary' : 'secondary'"
              @click="() => handleSetSorter(sorter)"
              class="tw:justify-between! tw:text-left"
              :icon="
                currentSorterKey === sorter.key
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

      <!-- Action buttons -->
      <div class="tw:flex tw:flex-col tw:gap-2 tw:xl:flex-row">
        <slot name="actions" />
      </div>
    </div>

    <Separator />

    <!-- No results message -->
    <div v-if="items.length === 0">
      <div
        class="tw:mx-auto tw:flex tw:max-w-[350px] tw:flex-col tw:items-center tw:text-center"
      >
        <PageTitle>{{ $t("global.no-results") }}</PageTitle>
        <p>{{ $t("global.no-items-found-try-different-search-term") }}</p>
      </div>
    </div>

    <!-- Items -->
    <template v-if="$slots.items || $slots.item">
      <CardGrid :columns="4">
        <template v-if="$slots.item">
          <slot
            v-for="item in items"
            :key="itemsIdKey ? item[itemsIdKey] : undefined"
            name="item"
            v-bind="{ ...item }"
          />
        </template>

        <template v-if="$slots.items">
          <slot name="items" v-bind="items" />
        </template>
      </CardGrid>
    </template>

    <!-- Pagination -->
    <div
      v-if="totalPages > 1"
      class="tw:mt-4 tw:flex tw:flex-wrap tw:justify-center tw:gap-2"
    >
      <!-- First page -->
      <Button
        v-if="totalPages > 2"
        :disabled="currentPage === 1"
        @click="firstPage"
        icon="tabler-chevrons-left"
        variant="outlined"
        size="md"
        type="button"
      />

      <!-- Previous page -->
      <Button
        :disabled="currentPage === 1"
        @click="previousPage"
        icon="tabler-chevron-left"
        variant="outlined"
        size="md"
        type="button"
      />

      <!-- Page numbers -->
      <Button
        v-for="page in totalPages"
        :key="page"
        :variant="currentPage == page ? 'solid' : 'outlined'"
        size="md"
        square
        @click="currentPage = page"
        type="button"
      >
        {{ page }}
      </Button>

      <!-- Next page -->
      <Button
        :disabled="currentPage === totalPages"
        @click="nextPage"
        icon="tabler-chevron-right"
        variant="outlined"
        size="md"
        type="button"
      />

      <!-- Last page -->
      <Button
        v-if="totalPages > 2"
        :disabled="currentPage === totalPages"
        @click="lastPage"
        icon="tabler-chevrons-right"
        variant="outlined"
        size="md"
        type="button"
      />
    </div>
  </div>
</template>
