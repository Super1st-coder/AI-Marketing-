<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { ProjectFormData } from "./ProjectForm.vue";
import ProjectsApi, {
  ProjectCreateResponse,
} from "@/services/projects/ProjectsApi";
import { appLocalesArray } from "@/plugins/i18n";

const { locale, t } = useI18n();
const route = useRoute();
const router = useRouter();

const brandId = useBrandId();

const { data, saveData, goNext, setDirtyStage } = useMultiStepFormContext<
  ProjectFormData | undefined
>();

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string().required(t("forms.required-field")).trim(),
      description: string().required(t("forms.required-field")).trim(),
      target_regions: string().required(t("forms.required-field")).trim(),
      language: string().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    name: data.value?.name,
    description: data.value?.description,
    target_regions: data.value?.target_regions,
    language:
      data.value?.language ??
      appLocalesArray.find((appLocale) => locale.value === appLocale.code)
        ?.apiName,
  },
});

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  let response: ProjectCreateResponse;
  if (data.value?.id) {
    // Update existing project
    response = await ProjectsApi.update(brandId, data.value.id, {
      name: values.name,
      language: values.language,
      description: values.description,
      target_regions: values.target_regions,
    });
  } else {
    // Create Project and save data
    response = await ProjectsApi.create(brandId, values);
  }

  // Set stage as dirty
  if (meta.value.dirty) {
    setDirtyStage("summary", true);
  }

  if (data.value?.id) {
    // Go to the next step
    saveData({ ...response.data });
    goNext({ isDirty: meta.value.dirty });
  } else {
    // Go to the settings page
    disableSaveAlert.value = true;
    await router.replace({
      name: "ProjectSettings",
      params: { projectId: response.data.id },
      query: route.query,
      hash: route.hash,
    });
  }
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=Htu-ELhzTAY"
    >
      {{ $t("projects.information.title") }}
      <template #description>
        {{ $t("projects.information.description") }}
      </template>
    </PageTitle>

    <FieldsContainer>
      <FieldTextarea
        name="name"
        :label="$t('projects.information.name.label')"
        :placeholder="$t('projects.information.name.placeholder')"
        orientation="horizontal"
        required
        speechRecognition
        :rows="1"
      />

      <FieldTextarea
        name="description"
        :label="$t('projects.information.description-field.label')"
        :placeholder="$t('projects.information.description-field.placeholder')"
        orientation="horizontal"
        required
        speechRecognition
        :rows="1"
      />

      <FieldTextarea
        name="target_regions"
        :label="$t('projects.information.target-regions.label')"
        :placeholder="$t('projects.information.target-regions.placeholder')"
        orientation="horizontal"
        required
        speechRecognition
        :rows="1"
      />

      <FieldLanguage
        name="language"
        :label="$t('projects.information.language.label')"
        orientation="horizontal"
        required
      />
    </FieldsContainer>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack type="button" outline :to="{ name: 'ProjectList' }" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
