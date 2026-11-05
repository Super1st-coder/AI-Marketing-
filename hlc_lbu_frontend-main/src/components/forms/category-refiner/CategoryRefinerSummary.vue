<script lang="ts" setup>
import { CategoryRefinerStyles, RefinerCategory } from "./categoryRefinerTypes";

interface Props {
  categories: RefinerCategory[];
  styles?: CategoryRefinerStyles;
  editable?: boolean;
}

defineProps<Props>();
const { t, te } = useI18n();

const emit = defineEmits<{
  edit: [category: string];
}>();
</script>

<template>
  <div class="tw:flex tw:items-center tw:gap-6">
    <h2 v-if="$slots.title" class="tw:min-w-fit tw:text-lg tw:font-extrabold">
      <slot name="title" />
    </h2>
    <Separator />
  </div>

  <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:xl:grid-cols-2">
    <CardBase
      v-for="category in categories"
      :key="category.name"
      is="div"
      class="tw:p-4"
    >
      <CardTitle
        class="tw:mb-5"
        :iconVariant="styles?.[category.name]?.variant ?? 'gray'"
        :icon="styles?.[category.name]?.icon ?? 'tabler-tag'"
      >
        {{
          te(`category-refiner.titles.${category.name}`)
            ? t(`category-refiner.titles.${category.name}`)
            : snakeCaseToText(category.name)
        }}

        <template v-if="editable" #after>
          <button @click="emit('edit', category.name)" type="button">
            <Icon icon="tabler-pencil" class="tw:text-2xl" />
          </button>
        </template>
      </CardTitle>

      <template
        v-if="category.items.length > 0"
        v-for="(item, index) in category.items"
      >
        <p class="tw:p-2 tw:text-sm">
          {{ item.name }}
        </p>
        <Separator v-if="index < category.items.length - 1" />
      </template>
      <p v-else class="tw:text-sm">{{ $t("global.no-items") }}</p>
    </CardBase>
  </div>
</template>
