<script setup lang="ts">
import { BrandFormColor } from "../BrandFormTabColors.vue";

interface Props {
  color: BrandFormColor;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  edit: [logo: BrandFormColor];
  delete: [category: BrandFormColor];
}>();

const handleEdit = () => {
  emit("edit", props.color);
};

const handleDelete = () => {
  emit("delete", props.color);
};
</script>

<template>
  <div>
    <CardBase borderRadius="md">
      <!-- Color Preview -->
      <div
        class="tw:min-h-[60px] tw:rounded-t-[16px]"
        :style="{ backgroundColor: color.hex }"
      ></div>

      <div class="tw:border-t tw:border-gray-300 tw:p-4">
        <!-- Header -->
        <div
          class="tw:mb-1.5 tw:flex tw:items-center tw:justify-between tw:gap-2"
        >
          <!-- Category -->
          <h3 class="tw:text-lg tw:font-bold">{{ color.name }}</h3>

          <!-- Options -->
          <ButtonDropdownIcon
            placement="bottom-end"
            icon="tabler-dots"
            size="lg"
          >
            <template #options>
              <ButtonDropdownOption
                @click="handleEdit"
                leftIcon="tabler-pencil"
              >
                {{ $t("global.edit") }}
              </ButtonDropdownOption>

              <ButtonDropdownOption
                @click="handleDelete"
                leftIcon="tabler-trash"
              >
                {{ $t("global.delete") }}
              </ButtonDropdownOption>
            </template>
          </ButtonDropdownIcon>
        </div>

        <!-- Hex Code -->
        <p class="tw:text-sm tw:text-secondary-text">
          {{ color.hex }}
        </p>
      </div>
    </CardBase>

    <!-- Source -->
    <BrandFormSourceHint :source="color.source" class="tw:mt-2" />
  </div>
</template>
