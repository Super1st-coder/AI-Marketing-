<script lang="ts" setup>
import ProjectsAPI from "@/services/legacy/ProjectsAPI";
import { toTypedSchema } from "@vee-validate/yup";
import { useRouter } from "vue-router";
import { object, string } from "yup";

const router = useRouter();
const isLoading = ref(false);

const schema = toTypedSchema(
  object().shape({
    projectName: string().required(),
  }),
);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Create the project
  const response = await ProjectsAPI.create(values.projectName);

  router.push({
    name: "AdGenerationProcess",
    params: { id: response.data.id },
  });
});
</script>

<template>
  <WizardCard>
    <form
      @submit="onSubmit"
      class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
    >
      <div>
        <WizardCardTitle>
          {{ $t("process.create-new-project.title") }}
        </WizardCardTitle>

        <WizardCardParagraph>
          {{ $t("process.create-new-project.description") }}
        </WizardCardParagraph>
      </div>

      <FieldsContainer>
        <FieldText
          name="projectName"
          :label="$t('process.create-new-project.project-name.label')"
          :placeholder="
            $t('process.create-new-project.project-name.placeholder')
          "
          class="tw:mb-1"
          required
        />
      </FieldsContainer>

      <WizardCardActions>
        <WizardButtonGoBack :to="{ name: 'Projects' }" />

        <WizardButtonNext :disabled="!meta.valid" :isLoading="isLoading" />
      </WizardCardActions>
    </form>
  </WizardCard>
</template>
