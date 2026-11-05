<script lang="ts" setup>
import { useField, useFieldError } from "vee-validate";

interface Props {
  name: string;
  rules?: string;
  label?: string;
  acceptedExtensions?: string;
  maxSize?: number;
}

const props = withDefaults(defineProps<Props>(), {
  // 25 mega bytes
  maxSize: 25 * 1024 * 1024,
});
const { t } = useI18n();

const allowedExtensions = computed(() => props.acceptedExtensions);

const { value: fileModel, setValue } = useField<File | string | undefined>(
  () => props.name,
  props.rules,
);
const localError = ref<string>();

const handleDelete = () => {
  localError.value = undefined;
  setValue(undefined);
};

const errorMessage = useFieldError(() => props.name);

const handleClick = (e: Event) => {
  const target = e.target as HTMLInputElement;
  // This allows uploading the same file again
  target.value = "";
  localError.value = undefined;
};

const handleChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  if (file.size > props.maxSize) {
    localError.value = t("forms.file-upload.file-size-error", {
      maxSize: formatFileSize(props.maxSize),
    });
    return;
  }

  localError.value = undefined;

  setValue(file, true);
};
</script>

<template>
  <div>
    <div class="tw:flex tw:items-center tw:justify-between">
      <input
        :id="name"
        :name="name"
        :accept="allowedExtensions"
        type="file"
        hidden
        @change="handleChange"
        @click="handleClick"
      />

      <div class="tw:text-sm">
        <p v-if="!fileModel" class="tw:text-gray-500">
          {{ $t("forms.file-upload.no-file-uploaded") }}
        </p>
        <p v-else-if="typeof fileModel === 'string'">{{ fileModel }}</p>
        <p v-else>{{ fileModel.name }}</p>
      </div>

      <Button
        as="label"
        :for="name"
        v-if="!fileModel"
        leftIcon="uil:cloud-upload"
        variant="text"
        color="secondary"
        class="tw:p-0! tw:text-sm tw:font-medium tw:text-gray-600! tw:normal-case"
      >
        {{ label }}
      </Button>
      <Button
        as="label"
        :for="name"
        v-else
        @click="handleDelete"
        leftIcon="tabler-x"
        variant="text"
        color="secondary"
        class="tw:p-0! tw:text-sm tw:font-medium tw:text-gray-600! tw:normal-case"
      >
        {{ $t("global.remove") }}
      </Button>
    </div>
    <FieldError>
      {{ errorMessage || localError }}
    </FieldError>
  </div>
</template>
