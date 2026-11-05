<script lang="ts" setup>
import { useField } from "vee-validate";

type Props = {
  name: string;

  label?: string;
  description?: string;
  placeholder?: string;
  required?: boolean;
  speechRecognition?: boolean;
  orientation?: "horizontal" | "vertical";
  hideLayout?: boolean;
  labelClass?: ClassName;
  disabled?: boolean;
  rows?: number;
  maxCharacters?: number;
  characterCounter?: boolean;

  attachmentsName: string;
  multipleAttachments?: boolean;
  disableAttachmentUpload?: boolean;
};

const props = withDefaults(defineProps<Props>(), {
  orientation: "vertical",
  rows: 3,
  attachmentsName: "textAreaAttachments",
});

const emit = defineEmits<{
  focus: [e: Event];
}>();

const isFocused = ref(false);

const {
  value: model,
  errorMessage,
  handleChange,
  setValue,
} = useField<string | undefined>(() => props.name, undefined);

const { input, textarea } = useTextareaAutosize({
  input: computed({
    get: () => model.value ?? "",
    set: (value) => {
      model.value = value;
    },
  }),
});

const handleFocus = (e: Event) => {
  isFocused.value = true;
  emit("focus", e);
};

const handleBlur = (e: Event) => {
  handleChange(e);
  isFocused.value = false;
};

const onSpeechRecognitionTextReady = (text: string) => {
  setValue((model.value ? `${model.value} ` : "") + text);
};

const displayAsError = computed(() => {
  if (errorMessage.value) {
    return true;
  }

  if (
    typeof model.value === "string" &&
    props.maxCharacters &&
    model.value.length > props.maxCharacters
  ) {
    return true;
  }

  return false;
});

// Files
const { value: filesModel, setValue: setFiles } = useField<File[]>(
  () => props.attachmentsName,
  undefined,
  { initialValue: [] },
);

const handleFileUpload = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (!input.files) return;

  const selectedFiles = Array.from(input.files);
  setFiles([...filesModel.value, ...selectedFiles], true);

  input.value = "";
};

const removeFile = (index: number) => {
  // Copy the files array and remove the index
  const fileList = [...filesModel.value];
  fileList.splice(index, 1);

  // Set the new files
  setFiles(fileList, true);
};

const handleLabelClick = (e: MouseEvent) => {
  // Only focus if clicking on the label itself or its padding, not on child interactive elements
  const target = e.target as HTMLElement;

  // Don't focus if clicking within a label that targets the attachments input
  const labelForAttachments = target.closest(
    `label[for="${props.attachmentsName}"]`,
  );
  if (labelForAttachments) {
    return;
  }

  // Focus the textarea when clicking on the label padding
  if (textarea.value) {
    textarea.value.focus();
  }
};
</script>

<template>
  <FieldBaseControl
    :name="name"
    :label="label"
    :description="description"
    :required="required"
    :error="errorMessage"
    :orientation="orientation"
    :hideLayout="hideLayout"
    :labelClass="labelClass"
  >
    <div class="tw:flex tw:items-start tw:gap-2 tw:md:gap-6">
      <label
        :for="name"
        class="tw:flex tw:w-full tw:cursor-text tw:flex-col tw:gap-3 tw:rounded-md tw:border tw:bg-white tw:p-4"
        :class="{
          'tw:border-error': displayAsError,
          'tw:border-outline-border': !displayAsError,
          'tw:border-2 tw:border-primary': isFocused,
          'tw:bg-[#F0F0F0]': disabled,
        }"
        @click="handleLabelClick"
      >
        <div
          class="tw:flex tw:grow-0 tw:flex-wrap tw:gap-2.5"
          v-if="filesModel.length > 0"
        >
          <div
            v-for="(file, index) in filesModel"
            :key="index"
            class="tw:relative tw:aspect-square tw:basis-32 tw:overflow-hidden tw:rounded-lg tw:border tw:border-outline-border tw:bg-[#F2F5F7]"
          >
            <button
              class="tw:absolute tw:top-0 tw:right-0 tw:p-2 tw:text-secondary tw:opacity-90"
              type="button"
              @click="removeFile(index)"
            >
              <Icon icon="tabler-circle-x-filled" class="tw:text-2xl" />
            </button>

            <ImgFile
              v-if="
                file.type === 'image/png' ||
                file.type === 'image/jpeg' ||
                file.type === 'image/webp'
              "
              :src="file"
              class="tw:h-full tw:w-full tw:object-cover"
            />

            <img
              v-if="file.type === 'application/pdf'"
              src="/images/icons/pdf.png"
              class="tw:h-full tw:w-full"
            />
          </div>
        </div>

        <textarea
          ref="textarea"
          g
          v-model="input"
          :id="name"
          :name="name"
          :placeholder="placeholder"
          :disabled="disabled"
          @focus="handleFocus"
          @blur="handleBlur"
          @change="handleChange"
          @input="handleChange($event, displayAsError)"
          :rows="rows"
          class="tw:w-full tw:resize-none tw:bg-transparent tw:outline-hidden"
          :class="{ 'tw:opacity-50': disabled }"
        />

        <div class="tw:flex tw:justify-end">
          <label :for="attachmentsName">
            <Button
              as="label"
              icon="tabler-plus"
              size="lg"
              variant="text"
              type="button"
              :for="attachmentsName"
              :disabled="disableAttachmentUpload"
            />
          </label>
        </div>
      </label>

      <input
        :id="attachmentsName"
        :name="attachmentsName"
        type="file"
        hidden
        @change="handleFileUpload"
        accept="image/png,image/jpeg,image/webp,application/pdf"
        :disabled="disableAttachmentUpload"
        :multiple="multipleAttachments"
      />

      <SpeechRecognitionButton
        v-if="speechRecognition"
        @textReady="onSpeechRecognitionTextReady"
        :disabled="disabled"
      />

      <slot name="buttons" />
    </div>

    <div
      v-if="characterCounter || maxCharacters"
      class="tw:text-base"
      :class="{
        'tw:text-error': displayAsError,
      }"
    >
      {{ typeof model === "string" ? model.length : 0 }}
      <span v-if="maxCharacters"> / {{ maxCharacters }}</span> characters
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
