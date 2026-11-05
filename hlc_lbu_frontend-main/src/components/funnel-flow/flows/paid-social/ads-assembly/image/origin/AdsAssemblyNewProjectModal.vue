<script setup lang="ts">
import AbyssaleIntegrationApi, {
  ProjectNotFoundInAbyssaleError,
} from "@/services/funnel-flow/paid-social/AbyssaleIntegrationApi";
import { AdMediaTemplate } from "@/services/funnel-flow/paid-social/AdsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { useI18n } from "vue-i18n";
import { object, string } from "yup";

const { t } = useI18n();

const emit = defineEmits<{ success: [id: number] }>();

const store = useFunnelPaidSocialAdsAssemblyStore();

const isOpen = defineModel<boolean>({ required: true });
const isLoadingTemplates = ref(false);
const templates = ref<AdMediaTemplate[]>([]);
const generalErrorMessage = ref<string | undefined>(undefined);

const schema = computed(() =>
  toTypedSchema(
    object({
      project_name: string().required(t("forms.required-field")),
      project_id: string().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, values } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    project_name: undefined,
    project_id: undefined,
  },
});

const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;

  try {
    const response = await AbyssaleIntegrationApi.create({
      brand_id: store.brandId,
      ...values,
    });

    isOpen.value = false;
    emit("success", response.data.id);
  } catch (error) {
    if (error instanceof ProjectNotFoundInAbyssaleError) {
      generalErrorMessage.value = t(
        "funnel-flow.paid-social.ads.origin.new-project-modal.errors.project-not-found",
      );
    } else {
      throw error;
    }
  }
});

// Clear templates and error when the project id changes
watch(
  () => values.project_id,
  () => {
    templates.value = [];
    generalErrorMessage.value = undefined;
  },
);

async function fetchTemplates() {
  if (!values.project_id) {
    templates.value = [];
    return;
  }

  isLoadingTemplates.value = true;
  templates.value = [];

  try {
    templates.value = (
      await AbyssaleIntegrationApi.getTemplateListByAbyssaleProjectId(
        store.brandId,
        values.project_id,
      )
    ).data;
  } catch (e: unknown) {
    console.error(e);

    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.origin.new-project-modal.errors.templates-load-failed",
    );
  } finally {
    isLoadingTemplates.value = false;
  }
}
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="865"
    closeButton
    v-slot="{ close }"
    alignment="top"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.ads.origin.new-project-modal.title") }}

      <template #description>
        {{
          $t("funnel-flow.paid-social.ads.origin.new-project-modal.description")
        }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldText
        name="project_name"
        :label="
          $t(
            'funnel-flow.paid-social.ads.origin.new-project-modal.project-name.label',
          )
        "
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.origin.new-project-modal.project-name.placeholder',
          )
        "
        class="tw:mb-10"
      />

      <FieldText
        name="project_id"
        :label="
          $t(
            'funnel-flow.paid-social.ads.origin.new-project-modal.project-id.label',
          )
        "
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.origin.new-project-modal.project-id.placeholder',
          )
        "
        class="tw:mb-6"
        :loading="isLoadingTemplates"
      >
        <template #right>
          <Link
            leftIcon="tabler:link"
            is="button"
            type="button"
            :disabled="!values.project_id"
            @click="fetchTemplates"
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.origin.new-project-modal.project-id.link",
              )
            }}
          </Link>
        </template>
      </FieldText>

      <Alert v-if="generalErrorMessage" type="error" class="tw:mt-6">
        {{ generalErrorMessage }}
      </Alert>

      <div v-if="templates.length > 0">
        <Separator class="tw:mb-5" />

        <AdsAssemblyTemplateGrid :templates="templates" />
      </div>
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        :uppercase="false"
        type="button"
        @click="close"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button
        :uppercase="false"
        :isLoading="isSubmitting"
        :disabled="isLoadingTemplates || templates.length === 0"
      >
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
