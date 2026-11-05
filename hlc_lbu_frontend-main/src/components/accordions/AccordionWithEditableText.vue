<script setup lang="ts">
import { IconCardVariant } from "../cards/IconCard.vue";

interface Props {
  name: string;
  title: string;
  icon?: string;
  variant?: IconCardVariant;
  editable?: boolean;

  type?: "text" | "textarea";
  placeholder?: string;
  disabled?: boolean;
}

const props = defineProps<Props>();

const { value: model } = useField<string>(() => props.name);
const errorMessage = useFieldError(() => props.name);
const isOpen = ref(false);

watch(errorMessage, () => {
  isOpen.value = true;
});
</script>

<template>
  <Accordion
    :title="title"
    :icon="icon"
    :iconVariant="variant"
    :color="errorMessage ? 'error' : 'default'"
    v-model="isOpen"
  >
    <FieldBaseEditableText
      v-if="editable"
      v-model="model"
      type="textarea"
      :placeholder="placeholder"
      preventScroll
      :required="false"
      :disabled="disabled"
    />
    <p v-else class="tw:whitespace-pre-line">
      {{ model }}
    </p>

    <template v-if="errorMessage" #footer>
      <FieldError v-if="errorMessage">{{ errorMessage }}</FieldError>
    </template>
  </Accordion>
</template>
