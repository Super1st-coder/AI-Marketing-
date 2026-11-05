<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, object, string } from "yup";
import NewBrandsApi from "@/services/NewBrandsApi";
const { t } = useI18n();

const store = useBrandFormStore();
const notificationStore = useNotificationStore();

function getIdentityFormValuesFromStore() {
  return {
    about_us: store.brand.identity.about_us?.value,
    mission: store.brand.identity.mission?.value,
    vision: store.brand.identity.vision?.value,
    values: store.brand.identity.values?.value,
    tone_of_voice: store.brand.identity.tone_voice?.value,
  };
}

function getIdentitySourcesFromStore() {
  return {
    about_us: store.brand.identity.about_us?.source,
    mission: store.brand.identity.mission?.source,
    vision: store.brand.identity.vision?.source,
    values: store.brand.identity.values?.source,
    tone_of_voice: store.brand.identity.tone_voice?.source,
  };
}

const sources = ref(getIdentitySourcesFromStore());

const schema = computed(() =>
  toTypedSchema(
    object({
      about_us: string().required(t("forms.required-field")).trim(),
      mission: string().required(t("forms.required-field")).trim(),
      vision: string().required(t("forms.required-field")).trim(),
      values: array()
        .of(string().required(t("forms.required-field").trim()))
        .min(1, t("forms.required-field"))
        .required(t("forms.required-field")),
      tone_of_voice: array()
        .of(string().required(t("forms.required-field")).trim())
        .min(1, t("forms.required-field"))
        .required(t("forms.required-field")),
    }),
  ),
);

const {
  handleSubmit,
  meta,
  isSubmitting,
  setFieldValue,
  values,
  submitSuccess,
  resetForm,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: getIdentityFormValuesFromStore(),
  resetDirtyOnSubmit: true,
});

// Keep identity form values in sync with store refetches
watch(
  () => [
    store.brand.identity.about_us?.value,
    store.brand.identity.mission?.value,
    store.brand.identity.vision?.value,
    store.brand.identity.values?.value,
    store.brand.identity.tone_voice?.value,
  ],
  () => {
    sources.value = getIdentitySourcesFromStore();

    resetForm({
      values: getIdentityFormValuesFromStore(),
    });
  },
  { deep: true },
);

async function save(showSuccessMessage = true) {
  // Update brand with new identity data
  await NewBrandsApi.update(store.brandId, {
    identity: {
      about_us: {
        value: values.about_us ?? "",
        source: sources.value.about_us ?? [],
      },
      mission: {
        value: values.mission ?? "",
        source: sources.value.mission ?? [],
      },
      vision: {
        value: values.vision ?? "",
        source: sources.value.vision ?? [],
      },
      values: {
        value: values.values ?? [],
        source: sources.value.values ?? [],
      },
      tone_voice: {
        value: values.tone_of_voice ?? [],
        source: sources.value.tone_of_voice ?? [],
      },
    },
  });

  // Refetch the whole brand
  await store.refetch();

  if (showSuccessMessage) {
    notificationStore.display({
      type: "success",
      title: t("brands.settings.assets-updated-toast.title"),
      description: t("brands.settings.assets-updated-toast.description"),
    });
  }
}

const onSubmit = handleSubmit(async () => {
  await save();
});

async function handleSaveAndExit() {
  await save(false);
}

// Research online functionality
const createFetcher = (
  attribute: "about_us" | "mission" | "vision" | "values" | "tone_voice",
) => {
  return async () => {
    const response = await NewBrandsApi.researchOnline({
      brand_id: store.brandId,
      attribute,
    });

    // Clear source
    sources.value[attribute] = [];

    return response.data.text;
  };
};

const createAiFetcher = (
  attribute: "about_us" | "mission" | "vision" | "values" | "tone_voice",
) => {
  return async () => {
    const response = await NewBrandsApi.generateIdentityWithAI({
      brand_id: store.brandId,
      attribute,
    });

    // Clear source
    sources.value[attribute] = [];

    return response.data.text;
  };
};

const handleAboutUsFetched = (text: string) => {
  setFieldValue("about_us", text);
};

const handleMissionFetched = (text: string) => {
  setFieldValue("mission", text);
};

const handleVisionFetched = (text: string) => {
  setFieldValue("vision", text);
};

const handleValuesFetched = (text: string) => {
  const values = text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line);

  setFieldValue("values", values);
};

const handleToneOfVoiceFetched = (text: string) => {
  const tones = text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line);

  setFieldValue("tone_of_voice", tones);
};

async function handleBeforeUpload() {
  try {
    await save(false);
  } catch (error) {
    console.log(error);
  }
}

async function handleAfterUpload() {
  await store.refetch();
  resetForm({
    values: getIdentityFormValuesFromStore(),
  });
}
</script>

<template>
  <BrandFormTabLayout :maxWidth="868" @submit.prevent="onSubmit">
    <BrandFormTabIdentityAlert
      v-if="store.displayGlobalAlert"
      class="tw:mb-10"
      :beforeSubmitFn="handleBeforeUpload"
      :afterSubmitFn="handleAfterUpload"
    />

    <PageTitle> {{ $t("brands.settings.identity.title") }} </PageTitle>

    <FieldsContainer>
      <FieldTextarea
        name="about_us"
        :label="$t('brands.settings.identity.about-us.label')"
        :placeholder="$t('brands.settings.identity.about-us.placeholder')"
        speechRecognition
        required
      >
        <template #hint>
          <BrandFormSourceHint
            :isEmpty="!values.about_us?.trim()"
            :source="sources.about_us"
            :fetcher="createFetcher('about_us')"
            :aiFetcher="createAiFetcher('about_us')"
            @fetched="handleAboutUsFetched"
          />
        </template>
      </FieldTextarea>

      <FieldTextarea
        name="mission"
        :label="$t('brands.settings.identity.mission.label')"
        :placeholder="$t('brands.settings.identity.mission.placeholder')"
        speechRecognition
        required
      >
        <template #hint>
          <BrandFormSourceHint
            :isEmpty="!values.mission?.trim()"
            :source="sources.mission"
            :fetcher="createFetcher('mission')"
            :aiFetcher="createAiFetcher('mission')"
            @fetched="handleMissionFetched"
          />
        </template>
      </FieldTextarea>

      <FieldTextarea
        name="vision"
        :label="$t('brands.settings.identity.vision.label')"
        :placeholder="$t('brands.settings.identity.vision.placeholder')"
        speechRecognition
        required
      >
        <template #hint>
          <BrandFormSourceHint
            :isEmpty="!values.vision?.trim()"
            :source="sources.vision"
            :fetcher="createFetcher('vision')"
            :aiFetcher="createAiFetcher('vision')"
            @fetched="handleVisionFetched"
          />
        </template>
      </FieldTextarea>

      <FieldComboBox
        name="values"
        :label="$t('brands.settings.identity.values.label')"
        required
      >
        <template #hint>
          <BrandFormSourceHint
            :isEmpty="!values.values || values.values.length === 0"
            :source="sources.values"
            :fetcher="createFetcher('values')"
            :aiFetcher="createAiFetcher('values')"
            @fetched="handleValuesFetched"
          />
        </template>
      </FieldComboBox>

      <FieldComboBox
        name="tone_of_voice"
        :label="$t('brands.settings.identity.tone-of-voice.label')"
        required
      >
        <template #hint>
          <BrandFormSourceHint
            :isEmpty="
              !values.tone_of_voice || values.tone_of_voice.length === 0
            "
            :source="sources.tone_of_voice"
            :fetcher="createFetcher('tone_voice')"
            :aiFetcher="createAiFetcher('tone_voice')"
            @fetched="handleToneOfVoiceFetched"
          />
        </template>
      </FieldComboBox>
    </FieldsContainer>

    <template #actions>
      <BrandFormGoToWorkspaceButton />

      <Button
        :disabled="!meta.dirty || submitSuccess"
        :isLoading="isSubmitting"
      >
        {{ $t("brands.settings.identity.save-changes") }}
      </Button>
    </template>
  </BrandFormTabLayout>

  <!-- Save locking -->
  <ModalFormSaveOrDiscard
    :isDirty="meta.dirty && !submitSuccess"
    :saveFn="handleSaveAndExit"
  />
</template>
