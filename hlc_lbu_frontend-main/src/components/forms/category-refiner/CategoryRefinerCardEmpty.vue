<script lang="ts" setup>
import SimpleFieldText from "@/components/forms/base/SimpleFieldText.vue";
import { useCategoryRefinerData } from "./useCategoryRefiner";
import { RefinerCategory } from "./categoryRefinerTypes";

const props = defineProps<{
  defaultProps?: Partial<RefinerCategory>;
}>();

const { data } = useCategoryRefinerData();
const fieldRef = ref<InstanceType<typeof SimpleFieldText>>();

const nameField = ref<string>("");

const handleSave = () => {
  const isDuplicated = data.value.find(
    (category) => category.name == nameField.value,
  );

  if (isDuplicated) {
    return;
  }

  data.value = [
    ...data.value,
    {
      name: nameField.value,
      items: [],
      hasBeenOpened: true,
      isOpen: true,
      canBeDeleted: true,
      ...props.defaultProps,
    },
  ];

  nameField.value = "";
  fieldRef.value?.input?.blur();
};
</script>

<template>
  <div
    class="tw:flex tw:flex-col tw:gap-1.5 tw:rounded-[20px] tw:bg-white tw:px-[15px] tw:py-5"
  >
    <h2 class="tw:grow tw:text-lg tw:font-extrabold">
      {{ $t("category-refiner.add-new-category") }}
    </h2>

    <form @submit.prevent="handleSave">
      <FieldBaseText
        ref="fieldRef"
        v-model="nameField"
        :placeholder="$t('category-refiner.write-a-name-placeholder')"
      />
    </form>
  </div>
</template>
