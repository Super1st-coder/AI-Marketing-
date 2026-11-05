<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object, string } from "yup";

const emit = defineEmits<{ create: [style: ImageStudioVisualStyle] }>();

const { t } = useI18n();
const isOpen = defineModel<boolean>({ required: true });

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string().required(t("forms.required-field")).trim(),
      image: mixed<File>().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    name: undefined,
    image: undefined,
  },
});

const onSubmit = handleSubmit(async (values) => {
  await sleep(2000);

  emit("create", {
    name: values.name,
    image: values.image,
  });

  isOpen.value = false;
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("image-studio.visual-styles.create-modal.title") }}

      <template #description>
        {{ $t("image-studio.visual-styles.create-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldText
          name="name"
          :label="$t('image-studio.visual-styles.create-modal.name.label')"
          :placeholder="
            $t('image-studio.visual-styles.create-modal.name.placeholder')
          "
          required
        />

        <FieldImage
          name="image"
          :label="$t('image-studio.visual-styles.create-modal.image.label')"
          :disabled="isSubmitting"
          required
          :acceptedFormats="['png', 'jpg', 'jpeg']"
          :maxSize="IMAGE_STUDIO_VISUAL_STYLE_MAX_FILE_SIZE_BYTES"
          :previewAspectRatio="552 / 200"
        >
          <template #inputTitle>
            {{ $t("image-studio.visual-styles.create-modal.image.upload") }}
          </template>
        </FieldImage>
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <template #before>
        <Button
          color="secondary"
          variant="outlined"
          type="button"
          @click="close"
        >
          {{ $t("global.cancel") }}
        </Button>
      </template>

      <Button :isLoading="isSubmitting" type="submit">
        {{ $t("image-studio.visual-styles.create") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
