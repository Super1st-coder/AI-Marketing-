<script setup lang="ts">
import { useDisplay } from "vuetify";

interface Props {
  itemsPerPage: number;
  totalItems: number;
}

const props = defineProps<Props>();
const { t } = useI18n();
const { xs } = useDisplay();

const page = defineModel<number>("page", { required: true });

const description = computed(() => {
  const start = (page.value - 1) * props.itemsPerPage + 1;
  const end = Math.min(page.value * props.itemsPerPage, props.totalItems);
  const total = props.totalItems;

  return t("global.pagination-showing-entries", {
    start: total === 0 ? 0 : start,
    end,
    total,
  });
});

const totalVisible = computed(() =>
  xs.value ? 1 : Math.min(Math.ceil(props.totalItems / props.itemsPerPage), 5),
);
</script>

<template>
  <div>
    <Separator />

    <div class="tw:flex tw:items-center tw:justify-between tw:px-5 tw:py-6">
      <p class="tw:text-secondary-text">
        {{ description }}
      </p>

      <VPagination
        v-model="page"
        :length="Math.ceil(totalItems / itemsPerPage)"
        :totalVisible="totalVisible"
      />
    </div>
  </div>
</template>
