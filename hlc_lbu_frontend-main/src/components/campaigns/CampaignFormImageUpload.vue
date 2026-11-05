<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object } from "yup";
import { CampaignFormData } from "./CampaignForm.vue";
import CampaignsApi from "@/services/projects/CampaignsApi";

const emit = defineEmits<{
  goBack: [];
}>();

const brandId = useBrandId();
const projectId = useProjectId();

const { data, saveData, goNext } = useMultiStepFormContext<CampaignFormData>();
const isLoading = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      image: mixed<ImageLibraryFile | string>().required(),
    }),
  ),
);

const { handleSubmit, isFieldDirty } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    image: data.value.thumbnail_url ?? undefined,
  },
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Erase attributes, so if the user goes back later, the upload screen will be loaded
  const response = await CampaignsApi.saveImageAttributes(
    brandId,
    projectId,
    data.value.id,
    {
      image_attributes_generated: null,
      image_attributes_saved: null,
    },
  );

  // Save data
  saveData({
    ...response.data,
  });

  // Upload image only if it has changed
  if (isFieldDirty("image") && values.image instanceof File) {
    if (values.image.raw) {
      const imageResponse = await CampaignsApi.uploadImage(
        brandId,
        projectId,
        data.value.id,
        values.image,
      );

      saveData({
        thumbnail_url: imageResponse.data.thumbnail_url,
      });
    } else {
      const imageResponse = await CampaignsApi.uploadImageFromImgLibrary(
        brandId,
        projectId,
        data.value.id,
        values.image.libraryId,
      );

      saveData({
        thumbnail_url: imageResponse.data.thumbnail_url,
      });
    }
  }

  goNext();
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isLoading">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=rZD4x4M9540"
    >
      {{ $t("campaigns.campaignsimage.image.upload.title") }}
      <template #description> </template>
    </PageTitle>

    <FieldsContainer>
      <FieldImageLibrary
        name="image"
        :label="$t('campaigns.campaignsimage.image.upload.label')"
        required
        class="tw:w-full tw:lg:max-w-[350px]"
        cropper
        :cropperAspectRatio="1 / 1"
      />
    </FieldsContainer>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="emit('goBack')" />
        <ButtonNext :isLoading="isLoading" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
