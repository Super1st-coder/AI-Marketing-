<script lang="ts" setup>
import FieldBaseText from "@/components/forms/base/FieldBaseText.vue";
import FieldBaseTextarea from "@/components/forms/base/FieldBaseTextarea.vue";

interface Props {
  editable?: boolean;
  deletable?: boolean;
  checkable?: boolean;
  required?: boolean;
  type?: "text" | "textarea";
  variant?: "default" | "text";
  color?: "normal" | "dark";
  preventScroll?: boolean;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  fit?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  editable: true,
  required: true,
  type: "text",
  variant: "default",
  color: "normal",
  fit: true,
});

const isEditing = ref(false);
const text = defineModel<string>({ required: false });
const checked = defineModel<boolean>("checked", { required: false });
const editedText = ref(text.value);

const emits = defineEmits<{
  delete: [];
}>();

const fieldRef = ref<InstanceType<typeof FieldBaseText>>();

const isValid = computed(() => {
  if (props.required) {
    return editedText.value !== "";
  }

  return true;
});

const handleEdit = async () => {
  isEditing.value = true;
  editedText.value = text.value;
  await nextTick();

  // We use a timeout here because otherwise preventScroll doesn't work in chrome
  setTimeout(() => {
    fieldRef.value?.focus({ preventScroll: props.preventScroll });
  }, 0);
};

const handleSubmit = () => {
  isEditing.value = false;

  if (isValid.value) {
    text.value = editedText.value;
  } else {
    editedText.value = text.value;
  }
};

const handleDelete = async () => {
  emits("delete");
};

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key == "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
};

const handleClickCancel = () => {
  editedText.value = text.value;
  handleSubmit();
};
</script>

<template>
  <div class="tw:font-medium">
    <div v-if="isEditing" class="tw:relative">
      <component
        :is="type === 'textarea' ? FieldBaseTextarea : FieldBaseText"
        ref="fieldRef"
        v-model="editedText"
        :placeholder="placeholder ?? $t('forms.write')"
        :disabled="disabled"
        @blur="handleSubmit"
        @keydown="handleKeyDown"
        :rows="1"
      >
        <template #right>
          <EditableElementIcon
            type="button"
            icon="tabler:x"
            class="tw:h-full tw:text-error"
            @mousedown.prevent="handleClickCancel"
          />
        </template>
      </component>
    </div>
    <!-- The text and some buttons when the text is not edited -->
    <div
      v-else
      class="tw:flex tw:gap-1.5"
      :class="{
        'tw:rounded tw:py-[10px] tw:pr-[12px] tw:pl-[16px]': variant !== 'text',
        'tw:bg-success-light tw:text-success': checked && variant === 'default',
        'tw:bg-[#F4F2F2]':
          !checked && color === 'normal' && variant === 'default',
        'tw:bg-outline-border':
          !checked && color === 'dark' && variant === 'default',
        'tw:w-fit': fit && variant === 'text',
        'tw:pointer-events-none tw:opacity-50': disabled && editable,
      }"
    >
      <!-- Text -->
      <div class="tw:grow">
        <p
          class="tw:tracking-[0.15px] tw:whitespace-pre-line"
          :class="{
            'tw:opacity-50': !text,
            'tw:leading-none': variant === 'text',
          }"
        >
          {{ text || placeholder || $t("forms.write") }}
        </p>
      </div>

      <!-- Buttons -->
      <div v-if="!isEditing" class="tw:flex tw:gap-2.5">
        <EditableElementIcon
          v-if="checkable"
          type="button"
          @click="checked = !checked"
          :icon="checked ? 'tabler-square-check-filled' : 'tabler-square'"
        />
        <EditableElementIcon
          v-if="editable"
          type="button"
          @click="handleEdit"
          icon="tabler-pencil"
        />
        <EditableElementIcon
          v-if="deletable"
          type="button"
          @click="handleDelete"
          icon="tabler-x"
        />
      </div>
    </div>

    <FieldError v-if="error">
      {{ error }}
    </FieldError>
  </div>
</template>
