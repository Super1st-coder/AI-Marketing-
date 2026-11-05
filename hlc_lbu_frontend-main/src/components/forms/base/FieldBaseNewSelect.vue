<script lang="ts" setup>
import { FieldInputBasicProps } from "./common-field-props";
import { toVuetifySelectItems } from "./select-option";
import type { SelectOption } from "./select-option";

export type { SelectOption, SelectOptionChip } from "./select-option";

export interface FieldBaseNewSelectProps extends FieldInputBasicProps {
  options: SelectOption[];
  multiple?: boolean;
  chips?: boolean;
  closableChips?: boolean;
  hideNoData?: boolean;
  clearable?: boolean;
}

const props = withDefaults(defineProps<FieldBaseNewSelectProps>(), {
  orientation: "vertical",
  clearable: true,
});

const model = defineModel<unknown>({ required: false });
const emit = defineEmits<{
  focus: [e: Event];
  blur: [e: Event];
  change: [value: unknown];
  clickLeftIcon: [e: MouseEvent];
  clickRightIcon: [e: MouseEvent];
}>();

const handleFocus = (e: Event) => {
  emit("focus", e);
};

const handleBlur = (e: Event) => {
  emit("change", e);
};

const handleChipClose = (itemValue: unknown) => {
  if (props.multiple && Array.isArray(model.value)) {
    model.value = model.value.filter((v) => v !== itemValue);
  } else {
    model.value = undefined;
  }
  emit("change", model.value);
};

const selectItems = computed(() => toVuetifySelectItems(props.options));

const hasOptionIcons = computed(() =>
  props.options.some(
    (option) =>
      option.type !== "subheader" &&
      option.type !== "divider" &&
      Boolean(option.icon),
  ),
);
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
    <div class="tw:flex tw:gap-2 tw:md:gap-6">
      <VSelect
        :id="name"
        :name="name"
        :items="selectItems"
        itemValue="value"
        itemTitle="label"
        item-props
        variant="outlined"
        class="custom-input"
        :class="props.inputClass"
        :placeholder="placeholder"
        v-model="model"
        :disabled="disabled"
        :clearable="clearable"
        @click:clear="model = undefined"
        @focus="handleFocus"
        @blur="handleBlur"
        :multiple="multiple"
        :chips="chips"
        :closableChips="closableChips"
        :loading="loading"
        :hideNoData="hideNoData"
      >
        <template #prepend-inner v-if="$slots.left || leftIcon">
          <FieldIcon
            v-if="leftIcon"
            :icon="leftIcon"
            :iconClass="leftIconClass"
            :clickable="leftIconClickable"
            @click="emit('clickLeftIcon', $event)"
          />

          <slot name="left" />
        </template>

        <template #append-inner v-if="$slots.right || rightIcon">
          <FieldIcon
            v-if="rightIcon"
            :icon="rightIcon"
            :iconClass="rightIconClass"
            :clickable="rightIconClickable"
            @click="emit('clickRightIcon', $event)"
          />

          <slot name="right" />
        </template>

        <template v-if="chips" #chip="{ item, internalItem }">
          <slot name="chip">
            <FieldSelectChip
              :closable="closableChips"
              @mousedown.stop="handleChipClose(item.value)"
            >
              {{ internalItem.title }}
            </FieldSelectChip>
          </slot>
        </template>

        <template #subheader="{ props: subheaderProps }">
          <VListSubheader class="tw:font-bold tw:text-primary-text">
            {{ subheaderProps.label ?? subheaderProps.title }}
          </VListSubheader>
        </template>

        <template #item="{ props: itemProps, item }">
          <slot name="item" v-bind="{ props: itemProps, item }">
            <VListItem
              v-bind="itemProps"
              :subtitle="item.subtitle"
              :prepend-avatar="item.image"
              :prepend-gap="8"
            >
              <template
                v-if="(item.icon || hasOptionIcons) && !item.image"
                #prepend
              >
                <div
                  class="tw:flex tw:h-5 tw:w-5 tw:shrink-0 tw:items-center tw:justify-center"
                >
                  <Icon
                    v-if="item.icon"
                    :icon="item.icon"
                    class="tw:text-xl"
                    :class="item.iconClass"
                  />
                </div>
              </template>

              <template v-if="item.chip" #append>
                <Chip
                  size="sm"
                  :color="item.chip.color"
                  :variant="item.chip.variant"
                  :custom-color="item.chip.customColor"
                  :left-icon="item.chip.leftIcon"
                  :icon="item.chip.icon"
                >
                  {{ item.chip.label }}
                </Chip>
              </template>
            </VListItem>
          </slot>
        </template>
      </VSelect>

      <slot name="buttons" />
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
