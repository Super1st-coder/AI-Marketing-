<script lang="ts" setup>
import { ref } from "vue";

export interface FieldComboBoxProps {
  name?: string;
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  orientation?: "horizontal" | "vertical";
  hideLayout?: boolean;
  labelClass?: ClassName;
}

withDefaults(defineProps<FieldComboBoxProps>(), {
  orientation: "vertical",
});

const tags = defineModel<string[] | undefined>(undefined);

const newTag = ref<string>("");
const showInput = ref<boolean>(false);
const inputRef = ref<HTMLInputElement | null>(null);

const openInput = () => {
  showInput.value = true;
  setTimeout(() => inputRef.value?.focus(), 0);
};

const addTag = () => {
  const tag = newTag.value.trim();
  if (!tag) {
    newTag.value = "";
    showInput.value = false;
    return;
  }

  if (tags.value) {
    tags.value = [...tags.value, tag];
  } else {
    tags.value = [tag];
  }

  newTag.value = "";
  showInput.value = false;
};

const removeTag = (index: number) => {
  if (!tags.value) return;

  tags.value = tags.value.filter((_tag, _index) => index !== _index);
};
</script>

<template>
  <FieldBaseControl
    :name="name"
    :label="label"
    :description="description"
    :required="required"
    :error="error"
    :orientation="orientation"
    :hideLayout="hideLayout"
    :labelClass="labelClass"
  >
    <div
      class="tw:flex tw:flex-wrap tw:gap-2 tw:rounded-xl tw:border tw:bg-white tw:p-4 tw:shadow-[0_1px_2px] tw:shadow-gray-900/5"
      :class="{
        'tw:border-gray-300': !error,
        'tw:border-error-500': error,
      }"
    >
      <div class="tw:flex tw:flex-wrap tw:gap-2">
        <span
          v-for="(tag, i) in tags"
          :key="i"
          class="tw:flex tw:gap-1 tw:rounded-xl tw:bg-gray-200 tw:pt-2.5 tw:pr-2 tw:pb-2.5 tw:pl-2.5 tw:text-gray-900"
        >
          {{ tag }}
          <button @click="removeTag(i)" class="tw:h-3.5 tw:w-3.5" type="button">
            ×
          </button>
        </span>

        <div v-if="showInput" class="tw:flex tw:items-center tw:gap-2">
          <input
            ref="inputRef"
            v-model="newTag"
            class="tw:h-11 tw:rounded-xl tw:border tw:border-primary-300 tw:px-4 tw:py-2.5 tw:text-gray-700 tw:shadow tw:focus:border-primary-300 tw:focus:outline-hidden"
          />
          <button
            type="button"
            @click="addTag"
            class="tw:flex tw:h-11 tw:w-11 tw:items-center tw:justify-center tw:rounded-lg tw:bg-primary tw:p-2 tw:text-white"
          >
            <Icon icon="tabler:check" class="tw:text-xl" />
          </button>
        </div>

        <button
          type="button"
          v-if="!showInput"
          @click="openInput"
          class="tw:h-11 tw:rounded-lg tw:border tw:border-gray-300 tw:bg-white tw:p-3 tw:text-black"
        >
          <Icon icon="tabler:plus" class="tw:text-xl" />
        </button>
      </div>
    </div>

    <template v-if="$slots.label" #label>
      <slot name="label" />
    </template>
    <template v-if="$slots.labelHelp" #labelHelp>
      <slot name="labelHelp" />
    </template>
    <template v-if="$slots.hint" #hint>
      <slot name="hint" />
    </template>
  </FieldBaseControl>
</template>
