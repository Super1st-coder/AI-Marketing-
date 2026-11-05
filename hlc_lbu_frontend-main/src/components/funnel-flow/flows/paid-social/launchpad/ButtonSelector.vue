<script setup lang="ts">
import { useField } from "vee-validate";

interface Props {
  options: {
    value: number | string;
    label: string;
    icon?: string;
    description?: string;
    disabled?: boolean;
  }[];
  name: string;
  cols: 2 | 4;
  label?: string;
  optional?: boolean;
}

const props = defineProps<Props>();

const {
  value: model,
  errorMessage,
  handleChange: _handleChange,
  handleBlur: _handleBlur,
} = useField<unknown | undefined>(() => props.name, undefined);

const handleChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.checked) {
    _handleChange(target.value);
  }
};

const handleBlur = (e: Event) => {
  _handleBlur(e);
};

const getName = (index: number) => {
  return `opt-${props.name}-${index}`;
};
</script>

<template>
  <FieldBaseControl
    :name="props.name"
    :label="props.label"
    :optional="props.optional"
    :error="errorMessage"
  >
    <!-- Cards/Buttons -->
    <ul
      class="tw:grid tw:grid-cols-1 tw:gap-4"
      :class="{
        'tw:md:grid-cols-2': props.cols === 2,
        'tw:lg:grid-cols-4': props.cols === 4,
      }"
    >
      <li v-for="(opt, index) in props.options" :key="index">
        <!-- Internal input -->
        <input
          :id="getName(index)"
          :name="props.name"
          :value="opt.value"
          type="radio"
          class="tw:peer tw:hidden"
          :disabled="opt.disabled"
          :checked="model === opt.value"
          @change="handleChange"
          @blur="handleBlur"
        />

        <!-- Body -->
        <label
          :for="getName(index)"
          class="tw:block tw:rounded-lg tw:border tw:border-gray-300 tw:peer-checked:border-2 tw:peer-checked:border-primary"
          :class="{
            'tw:px-3.5 tw:py-2.5': !opt.description,
            'tw:px-4 tw:py-5': opt.description,

            'tw:cursor-pointer tw:bg-white': !opt.disabled,
            'tw:cursor-not-allowed tw:bg-gray-100': opt.disabled,
          }"
        >
          <div class="tw:flex tw:items-start">
            <!-- Header -->
            <div
              class="tw:flex tw:grow"
              :class="{
                'tw:items-center tw:gap-2': !opt.description,
                'tw:flex-col tw:gap-5': opt.description,

                'tw:text-gray-500': opt.disabled,
              }"
            >
              <!-- Icon -->
              <Icon v-if="opt.icon" :icon="opt.icon" class="tw:text-xl" />

              <!-- Label -->
              <span class="tw:text-sm tw:font-semibold">{{ opt.label }}</span>
            </div>

            <!-- Optional soon chip -->
            <span
              v-if="opt.disabled"
              class="tw:rounded-full tw:bg-gray-300 tw:px-2 tw:py-[3px] tw:text-xs tw:font-medium tw:text-gray-500"
            >
              {{ $t("global.soon") }}
            </span>
          </div>

          <!-- Optional description -->
          <p
            v-if="opt.description"
            class="tw:mt-2 tw:text-xs tw:text-secondary"
          >
            {{ opt.description }}
          </p>
        </label>
      </li>
    </ul>
  </FieldBaseControl>
</template>
