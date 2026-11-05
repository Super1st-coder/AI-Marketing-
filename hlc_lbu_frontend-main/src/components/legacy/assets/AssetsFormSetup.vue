<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { AssetsFormData } from "./AssetsForm.vue";
import CampaignsApi from "@/services/projects/CampaignsApi";
import AssetsApi, { AssetSimpleTemplate } from "@/services/legacy/AssetsApi";

const { t } = useI18n();

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const { data, saveData, goNext } = useMultiStepFormContext<AssetsFormData>();

const selectedTemplate = useLocalStorage<string | undefined>(
  `brands.${brandId}.assets.${campaignId}.currentTemplate`,
  undefined,
);

// Fetch templates initially if the project is available
const templates = ref<AssetSimpleTemplate[]>(
  data.value.projectId
    ? (await AssetsApi.getTemplateList(brandId, projectId, campaignId)).data
    : [],
);

const schema = computed(() =>
  toTypedSchema(
    object({
      projectId: string()
        .required(t("forms.required-field"))
        .matches(
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
          t("campaigns.assets.setup.errormessage"),
        ),
    }),
  ),
);

const { handleSubmit, isSubmitting, validateField, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      projectId: data.value.projectId,
    },
  });

onMounted(() => {
  validateField("projectId");
  selectedTemplate.value = undefined;
});

const onSubmit = handleSubmit(async (values) => {
  // Save the data
  saveData({ projectId: values.projectId });
  await CampaignsApi.setAssetPlatformProjectId(
    brandId,
    projectId,
    campaignId,
    values.projectId,
  );

  // Fetch templates
  templates.value = (
    await AssetsApi.getTemplateList(brandId, projectId, campaignId)
  ).data;
});

const handleSelectTemplate = async (templateId: string) => {
  selectedTemplate.value = templateId;
  // If we don't wait for the next tick, the value of selectedTemplate is not written to the
  // local storage for some reason.
  await nextTick();

  saveData({ currentTemplateId: templateId, currentImageIndex: undefined });
  goNext();
};
</script>

<template>
  <FormStepLayout as="div">
    <PageTitle helpButton>
      {{ $t("campaigns.assets.setup.title") }}

      <template #description>
        {{ $t("campaigns.assets.setup.description") }}
      </template>
    </PageTitle>

    <FieldsContainer class="tw:grow">
      <form
        @submit.prevent="onSubmit"
        class="tw:flex tw:flex-col tw:gap-4 tw:lg:flex-row tw:lg:items-start"
      >
        <FieldText
          class="tw:grow"
          name="projectId"
          :label="$t('campaigns.assets.setup.projectIdLabel')"
          :placeholder="$t('campaigns.assets.setup.projectIdPlaceholder')"
          orientation="horizontal"
          required
        />

        <Button
          :isLoading="isSubmitting"
          :variant="data.projectId ? 'solid' : 'outlined'"
          :disabled="isSubmitting"
        >
          {{
            data.projectId
              ? $t("campaigns.assets.setup.buttonLinked")
              : $t("campaigns.assets.setup.buttonLink")
          }}
        </Button>
      </form>

      <template v-if="templates.length > 0">
        <Separator />

        <CardGrid>
          <button
            v-for="template in templates"
            type="button"
            @click="handleSelectTemplate(template.template_id)"
            class="tw:text-left"
          >
            <CardBase
              hoverColor="primary"
              class="tw:flex tw:flex-col tw:gap-5 tw:p-5"
            >
              <h2 class="tw:text-lg tw:font-extrabold">
                {{ template.template_name }}
              </h2>

              <Separator />

              <img
                :src="template.template_preview_url"
                class="tw:aspect-square tw:rounded-lg tw:bg-[#D9D9D9] tw:object-contain"
              />

              <Chip class="tw:self-start" color="secondary" variant="label">
                {{ $t("campaigns.assets.setup.chipStatic") }}
              </Chip>
            </CardBase>
          </button>
        </CardGrid>
      </template>
    </FieldsContainer>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
