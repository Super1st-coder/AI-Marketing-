<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object } from "yup";
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";

const emit = defineEmits<{
  goBack: [];
}>();

const brandId = useBrandId();
const projectId = useProjectId();

const { data, saveData, goNext } =
  useMultiStepFormContext<UmbrellaCampaignFormData>();
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
  const response = await UmbrellaCampaignsApi.saveImageAttributes(
    brandId,
    projectId,
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
      const imageResponse = await UmbrellaCampaignsApi.uploadImage(
        brandId,
        projectId,
        data.value.id,
        values.image,
      );

      saveData({
        thumbnail_url: imageResponse.data.thumbnail_url,
      });
    } else {
      const imageResponse =
        await UmbrellaCampaignsApi.uploadImageFromImgLibrary(
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
      helpVideoUrl="https://www.youtube.com/watch?v=uB81rH44TZU"
    >
      {{ $t("campaigns.campaignsimage.image.upload.title") }}
      <template #description> </template>
    </PageTitle>

    <FieldsContainer>
      <FieldImageLibrary
        name="image"
        :label="$t('umbrella-campaign.step-image.upload-field-label')"
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
