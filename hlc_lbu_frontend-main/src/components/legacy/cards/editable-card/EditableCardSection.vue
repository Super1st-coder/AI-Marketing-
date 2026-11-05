<script setup lang="ts">
import { IconCardVariant } from "@/components/cards/IconCard.vue";
import { useField } from "vee-validate";

interface Props {
  name: string;
  title?: string;
  icon?: string;
  iconVariant?: IconCardVariant;
  editable?: boolean;
  required?: boolean;
  placeholder?: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  required: true,
});

const { value, setValue } = useField<string | string[]>(() => props.name);

const errorMessage = useFieldError(() => props.name);

const text = ref<string | string[]>(value.value);

watch(text, (value) => {
  setValue(value);
});
</script>

<template>
  <div>
    <CardTitle :icon="icon" :iconVariant="iconVariant" class="tw:mb-3">
      {{ title }}<span v-if="editable && required">*</span>
    </CardTitle>

    <div v-if="Array.isArray(value)" class="tw:flex tw:flex-col tw:gap-3">
      <EditableCardSectionListItem
        v-if="editable"
        v-for="(_item, index) in value"
        :name="name"
        :index="index"
        :required="required"
        :placeholder="placeholder"
        :disabled="disabled"
      />
      <CardParagraph v-else v-for="item in value">
        {{ item }}
      </CardParagraph>
    </div>
    <template v-else>
      <FieldEditableText
        v-if="editable"
        :name="name"
        :required="required"
        :placeholder="placeholder"
        :disabled="disabled"
      />
      <CardParagraph v-else>
        {{ value }}
      </CardParagraph>
    </template>

    <FieldError v-if="errorMessage">
      {{ errorMessage }}
    </FieldError>
  </div>
</template>
