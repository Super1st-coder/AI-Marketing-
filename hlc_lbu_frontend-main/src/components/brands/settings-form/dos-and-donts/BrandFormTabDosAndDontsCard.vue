<script setup lang="ts">
import { BrandFormRule } from "../BrandFormTabDosAndDonts.vue";

interface Props {
  rule: BrandFormRule;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  edit: [rule: BrandFormRule];
  delete: [rule: BrandFormRule];
}>();

const handleEdit = () => {
  emit("edit", props.rule);
};

const handleDelete = () => {
  emit("delete", props.rule);
};
</script>

<template>
  <div>
    <CardBase class="tw:flex tw:items-start tw:p-2" borderRadius="md">
      <!-- Image Preview -->
      <CardBase
        class="tw:aspect-square tw:shrink-0 tw:basis-[112px] tw:overflow-hidden"
        color="secondary"
        borderRadius="sm"
      >
        <ImgFile
          v-if="rule.image"
          :src="rule.image"
          class="tw:h-full tw:w-full tw:object-cover"
        />
      </CardBase>

      <div class="tw:grow tw:p-4">
        <!-- Header -->
        <div
          class="tw:mb-2.5 tw:flex tw:items-center tw:justify-between tw:gap-2"
        >
          <!-- Rule Label -->
          <span class="tw:text-sm tw:font-medium tw:text-gray-500">
            {{ $t("brands.settings.dos-and-donts.rule-label") }}
          </span>

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

        <!-- Rule Text -->
        <p class="tw:text-sm tw:font-medium">
          {{ rule.text }}
        </p>
      </div>
    </CardBase>

    <!-- Source -->
    <BrandFormSourceHint :source="rule.source" class="tw:mt-2" />
  </div>
</template>
