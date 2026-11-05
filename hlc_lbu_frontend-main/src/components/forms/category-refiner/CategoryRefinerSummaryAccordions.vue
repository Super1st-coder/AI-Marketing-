<script lang="ts" setup>
import { CategoryRefinerStyles, RefinerCategory } from "./categoryRefinerTypes";

interface Props {
  categories: RefinerCategory[];
  styles?: CategoryRefinerStyles;
}

defineProps<Props>();

const { t, te } = useI18n();
</script>

<template>
  <AccordionList>
    <Accordion
      v-for="category in categories"
      :iconVariant="styles?.[category.name]?.variant ?? 'gray'"
      :icon="styles?.[category.name]?.icon ?? 'tabler-tag'"
    >
      <template #title>
        {{
          te(`category-refiner.titles.${category.name}`)
            ? t(`category-refiner.titles.${category.name}`)
            : snakeCaseToText(category.name)
        }}
      </template>

      <template v-if="category.items.length > 0">
        <p v-for="item in category.items" class="tw:text-sm">
          {{ item.name }}
        </p>
      </template>
      <p v-else class="tw:text-sm">{{ $t("global.no-items") }}</p>
    </Accordion>
  </AccordionList>
</template>
