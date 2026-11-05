<script setup lang="ts">
import type { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import CampaignsApi, { CampaignData } from "@/services/projects/CampaignsApi";
import ProjectsApi, { ProyectData } from "@/services/projects/ProjectsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { number, object } from "yup";

const { t } = useI18n();
const router = useRouter();
const brandId = useBrandId();

const isOpen = defineModel<boolean>({ required: true });

const schema = computed(() =>
  toTypedSchema(
    object({
      projectId: number().required(t("forms.required-field")),
      campaignId: number().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, resetForm, values, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
  });

// Fetch all projects of the brand
const projectsList = ref<ProyectData[]>(
  await fetchAllItems((range) =>
    ProjectsApi.getList(brandId, {
      range,
      order: { updatedAt: "desc" },
    }),
  ),
);

// Options for the project select field
const projectOptions = computed<AutocompleteOption[]>(() =>
  [...projectsList.value]
    .sort((a, b) => Number(b.status === "A") - Number(a.status === "A"))
    .map((project) => ({
      label: project.name,
      value: project.id,
      disabled: project.status !== "A",
      chip:
        project.status !== "A"
          ? {
              label: t("global.incomplete"),
              color: "error",
              variant: "label",
            }
          : undefined,
    })),
);

// List of campaigns
const areCampaignsLoading = ref(false);
const campaignList = ref<CampaignData[]>();

// Options for the campaign select field
const campaignOptions = computed<AutocompleteOption[]>(() =>
  campaignList.value
    ? [...campaignList.value]
        .sort((a, b) => Number(b.complete) - Number(a.complete))
        .map((campaign) => ({
          label: campaign.name,
          value: campaign.id,
          disabled: !campaign.complete,
          chip: !campaign.complete
            ? {
                label: t("global.incomplete"),
                color: "error",
                variant: "label",
              }
            : undefined,
        }))
    : [],
);

// Fetch campaigns
watch(
  () => values.projectId,
  async (projectId) => {
    // Clear campaigns
    campaignList.value = undefined;
    setFieldValue("campaignId", undefined, false);

    if (projectId) {
      // Fetch campaigns
      areCampaignsLoading.value = true;
      campaignList.value = await fetchAllItems((range) =>
        CampaignsApi.getList(brandId, projectId, {
          range,
          order: { updatedAt: "desc" },
        }),
      );
      areCampaignsLoading.value = false;
    }
  },
);

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  router.push({
    name: "FunnelFlowHome",
    params: { projectId: values.projectId, campaignId: values.campaignId },
  });
});

// Reset form when modal is closed
watch(
  () => isOpen.value,
  (isOpen) => {
    if (!isOpen) {
      resetForm();
    }
  },
);
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("brands.home.go-to-funnel-modal.title") }}

      <template #description>
        {{ $t("brands.home.go-to-funnel-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldAutocomplete
          name="projectId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-funnel-modal.project.label')"
          :placeholder="t('brands.home.go-to-funnel-modal.project.placeholder')"
          :options="projectOptions"
        />

        <FieldAutocomplete
          v-if="values.projectId"
          name="campaignId"
          leftIcon="tabler:search"
          :label="t('brands.home.go-to-funnel-modal.campaign.label')"
          :placeholder="
            t('brands.home.go-to-funnel-modal.campaign.placeholder')
          "
          :options="campaignOptions"
          :loading="areCampaignsLoading"
        />
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" @click="close" type="button">
        {{ $t("global.cancel") }}
      </Button>
      <Button>
        {{ $t("brands.home.go-to-funnel-modal.submit") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
