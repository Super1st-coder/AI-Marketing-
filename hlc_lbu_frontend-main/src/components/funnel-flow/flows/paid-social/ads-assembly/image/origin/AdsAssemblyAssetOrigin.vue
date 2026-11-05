<script setup lang="ts">
import AbyssaleIntegrationApi from "@/services/funnel-flow/paid-social/AbyssaleIntegrationApi";
import { UnidentifiedError } from "@/services/common-errors";
import { AdMediaTemplate } from "@/services/funnel-flow/paid-social/AdsApi";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import { toTypedSchema } from "@vee-validate/yup";
import { useI18n } from "vue-i18n";
import { number, object } from "yup";

const { t } = useI18n();

const store = useFunnelPaidSocialAdsAssemblyStore();
const paidSocialFormStore = useFunnelPaidSocialFormStore();

const projectOptions = computed(() =>
  store.projects.map((project) => ({
    value: project.id,
    label: project.project_name,
  })),
);

const isLoadingTemplates = ref(false);
const templates = ref<AdMediaTemplate[]>([]);
const isNewProjectModalOpen = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      projectId: number().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, values, setFieldValue, isFieldDirty } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      projectId: store.currentSet?.media_platform_project_id ?? undefined,
    },
  });

const onSubmit = handleSubmit(async (values) => {
  if (!store.campaign || !store.currentSet) {
    throw new UnidentifiedError();
  }

  if (isFieldDirty("projectId")) {
    await AdStructureApi.SetAbbysaleProjectToAdSet({
      brand_id: store.brandId,
      campaign_id: store.campaign.id,
      ad_set_id: store.currentSet?.id,
      media_platform_project_id: values.projectId,
    });

    // Revalidate funnel flow, so the form knows a template project is linked
    await paidSocialFormStore.revalidate();
  }

  await store.refetchAdSets();

  store.setScreen("settings");
});

const selectedProject = computed(() =>
  store.projects.find((project) => project.id === values.projectId),
);

async function fetchProjects() {
  isLoadingTemplates.value = true;

  await store.refetchAssetOrigins();

  isLoadingTemplates.value = false;
}

async function fetchTemplates() {
  templates.value = [];

  if (!values.projectId) {
    isLoadingTemplates.value = false;
    return;
  }

  isLoadingTemplates.value = true;

  templates.value = (
    await AbyssaleIntegrationApi.getTemplateListByProject(
      store.brandId,
      values.projectId,
    )
  ).data;

  isLoadingTemplates.value = false;
}

// Initial fetch
await fetchTemplates();

// Refetch templates on project change
watch(
  () => values.projectId,
  () => {
    fetchTemplates();
  },
  {},
);

function handleAddProject() {
  isNewProjectModalOpen.value = true;
}

async function handleAddProjectSuccess(id: number) {
  await fetchProjects();
  setFieldValue("projectId", id);
}
</script>

<template>
  <FormStepLayout :maxWidth="910" @submit.prevent="onSubmit">
    <template #stepper>
      <AdsAssemblyImageStepper />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=r1462xlXJOQ"
    >
      {{ $t("funnel-flow.paid-social.ads.origin.title") }}

      <template #description>
        {{ $t("funnel-flow.paid-social.ads.origin.description") }}
      </template>
    </PageTitle>

    <FieldNewSelect
      name="projectId"
      :placeholder="
        $t('funnel-flow.paid-social.ads.origin.project-search-placeholder')
      "
      :options="projectOptions"
      chips
      :loading="isLoadingTemplates"
      :disabled="isLoadingTemplates"
    >
      <template v-if="selectedProject" #chip>
        <span class="tw:line-clamp-1">
          <span class="tw:text-primary-text">
            {{ selectedProject.project_name }}
          </span>
          {{ " " }}
          <span class="tw:text-gray-500">
            {{ selectedProject.project_id }}
          </span>
        </span>
      </template>

      <template #buttons>
        <Link
          leftIcon="tabler:plus"
          is="button"
          type="button"
          class="tw:block tw:text-sm tw:font-medium"
          @click.stop="handleAddProject"
        >
          {{ $t("funnel-flow.paid-social.ads.origin.new-project-link") }}
        </Link>
      </template>
    </FieldNewSelect>

    <template v-if="store.projects.length > 0">
      <AdsAssemblyTemplateGrid
        v-if="templates.length > 0"
        :templates="templates"
      />
      <div
        v-else
        class="tw:mx-auto tw:flex tw:max-w-72 tw:flex-col tw:items-center tw:py-16 tw:text-secondary-text"
      >
        <Icon icon="tabler:eye" class="tw:mb-3 tw:text-2xl" />

        <p class="tw:text-sm">
          {{ $t("funnel-flow.paid-social.ads.origin.view-template") }}
        </p>
      </div>
    </template>
    <template v-else>
      <div class="tw:mx-auto tw:py-16 tw:text-center" style="max-width: 300px">
        <h2 class="tw:mb-3 tw:font-semibold">
          {{ $t("funnel-flow.paid-social.ads.origin.empty-state.title") }}
        </h2>

        <p class="tw:mb-6 tw:text-sm tw:text-secondary-text">
          {{ $t("funnel-flow.paid-social.ads.origin.empty-state.description") }}
        </p>

        <Button type="button" @click="handleAddProject" :uppercase="false">
          {{ $t("funnel-flow.paid-social.ads.origin.empty-state.link-now") }}
        </Button>
      </div>
    </template>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="store.setScreen('home')" />

        <Button :isLoading="isSubmitting" :uppercase="false">
          {{ $t("funnel-flow.paid-social.ads.origin.link-project") }}
        </Button>
      </WizardCardActions>
    </template>

    <AdsAssemblyNewProjectModal
      v-if="isNewProjectModalOpen"
      v-model="isNewProjectModalOpen"
      @success="handleAddProjectSuccess"
    />
  </FormStepLayout>
</template>
