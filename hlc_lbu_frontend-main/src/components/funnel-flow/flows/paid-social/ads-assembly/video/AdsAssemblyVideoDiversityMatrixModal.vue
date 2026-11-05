<script setup lang="ts">
import { DataTableHeader } from "vuetify";
import {
  VideoScriptAndromedaScores,
  VideoScriptVariant,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { videoScriptScoreColorClass } from "./videoScriptScore";

const ANDROMEDA_AXES = [
  "resonancia",
  "autenticidad",
  "claridad",
  "marca",
  "accion",
] as const satisfies readonly (keyof VideoScriptAndromedaScores)[];

type MatrixRow = {
  key: (typeof ANDROMEDA_AXES)[number] | "overall";
  label: string;
  scores: (number | null)[];
};

const props = defineProps<{
  variants: VideoScriptVariant[];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();

const variantColumns = computed(() =>
  props.variants.map((_variant, index) => ({
    key: `variant-${index}`,
    title: t("funnel-flow.paid-social.ads.video.variant-tab-short", {
      number: index + 1,
    }),
  })),
);

const headers = computed<DataTableHeader<MatrixRow>[]>(() => [
  {
    title: t("funnel-flow.paid-social.ads.video.diversity-matrix.axis-column"),
    key: "label",
    sortable: false,
  },
  ...variantColumns.value.map((column) => ({
    title: column.title,
    key: column.key,
    sortable: false,
  })),
]);

// Rows: the 5 Andromeda axes, plus the overall score at the bottom
const rows = computed<MatrixRow[]>(() => [
  ...ANDROMEDA_AXES.map((axis) => ({
    key: axis,
    label: t(`funnel-flow.paid-social.ads.video.diversity-matrix.axes.${axis}`),
    scores: props.variants.map((variant) => variant.andromeda?.[axis] ?? null),
  })),
  {
    key: "overall" as const,
    label: t("funnel-flow.paid-social.ads.video.diversity-matrix.axes.overall"),
    scores: props.variants.map((variant) => variant.score),
  },
]);

function formatScore(score: number | null) {
  return score !== null ? score.toFixed(1) : "—";
}
</script>

<template>
  <ModalGeneric v-model="isOpen" :maxWidth="750">
    <template #title>
      {{
        $t("funnel-flow.paid-social.ads.video.diversity-matrix.title", {
          axisCount: ANDROMEDA_AXES.length,
          variantCount: variants.length,
        })
      }}
    </template>

    <VDataTable
      :items="rows"
      :headers="headers"
      itemValue="key"
      :items-per-page="-1"
      hide-default-footer
    >
      <template #item.label="{ item }">
        <span class="tw:font-bold">{{ item.label }}</span>
      </template>

      <template
        v-for="(column, columnIndex) in variantColumns"
        :key="column.key"
        #[`item.${column.key}`]="{ item }"
      >
        <span
          class="tw:font-semibold"
          :class="videoScriptScoreColorClass(item.scores[columnIndex])"
        >
          {{ formatScore(item.scores[columnIndex]) }}
        </span>
      </template>
    </VDataTable>
  </ModalGeneric>
</template>
