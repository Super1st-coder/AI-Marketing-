<script setup lang="ts">
import type { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import ProjectsApi, { ProyectData } from "@/services/projects/ProjectsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const { t } = useI18n();
const router = useRouter();
const brandId = useBrandId();

const isOpen = defineModel<boolean>({ required: true });

const schema = computed(() =>
  toTypedSchema(
    object({
      projectId: string().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, resetForm } = useFormWithErrorScrolling({
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

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  router.push({
    name: "CreateUmbrellaCampaign",
    params: { projectId: values.projectId },
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
      {{ $t("brands.home.create-umbrella-campaign-modal.title") }}

      <template #description>
        {{ $t("brands.home.create-umbrella-campaign-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldAutocomplete
        name="projectId"
        leftIcon="tabler:search"
        :placeholder="
          t('brands.home.create-umbrella-campaign-modal.select-placeholder')
        "
        :options="projectOptions"
      />
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" @click="close" type="button">
        {{ $t("global.cancel") }}
      </Button>
      <Button>
        {{ $t("brands.home.create-umbrella-campaign-modal.submit") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
