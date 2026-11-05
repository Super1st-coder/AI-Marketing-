<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object } from "yup";
import { TargetCustomerFormData } from "../TargetCustomerForm.vue";
import BuyerPersonasApi from "@/services/BuyerPersonasApi";

const emit = defineEmits<{
  goBack: [];
}>();

const brandId = useBrandId();

const { data, saveData, goNext } =
  useMultiStepFormContext<TargetCustomerFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      image: mixed<ImageLibraryFile | string>().required(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta, isFieldDirty } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      image: data.value.thumbnail_url ?? undefined,
    },
  });

const onSubmit = handleSubmit(async (values) => {
  // Erase attributes, so if the user goes back later, the upload screen will be loaded
  const response = await BuyerPersonasApi.saveImageAttributes(
    brandId,
    data.value.id,
    {
      image_attributes_generated: null,
      image_attributes_saved: null,
    },
  );

  saveData({
    ...response.data,
  });

  // Upload image only if it has changed
  if (isFieldDirty("image") && values.image instanceof File) {
    if (values.image.raw) {
      const imageResponse = await BuyerPersonasApi.uploadImage(
        brandId,
        data.value.id,
        values.image,
      );

      saveData({
        thumbnail_url: imageResponse.data.thumbnail_url,
      });
    } else {
      const imageResponse = await BuyerPersonasApi.uploadImageFromImgLibrary(
        brandId,
        data.value.id,
        values.image.libraryId,
      );

      saveData({
        thumbnail_url: imageResponse.data.thumbnail_url,
      });
    }
  }

  goNext({ isDirty: meta.value.dirty });
});
</script>

<template>
  <FormStepLayout
    @submit.prevent="onSubmit"
    :disabled="data.locked || isSubmitting"
  >
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=Kqw5Y6v0SoM"
    >
      {{ $t("buyer-person.image.legacy.upload.title") }}

      <template #description>
        {{ $t("buyer-person.image.legacy.upload.description") }}
      </template>
    </PageTitle>

    <FieldsContainer>
      <FieldImageLibrary
        name="image"
        :label="$t('forms.image.label')"
        required
        class="tw:w-full tw:lg:max-w-[350px]"
        cropper
        :cropperAspectRatio="1 / 1"
      />
    </FieldsContainer>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="emit('goBack')" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
