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

const { handleSubmit, isSubmitting, resetForm } = useFormWithErrorScrolling({
  validationSchema: schema,
});

const projectsList = ref<ProyectData[]>([]);
const isLoadingProjects = ref(false);

async function loadProjects() {
  isLoadingProjects.value = true;
  try {
    projectsList.value = await fetchAllItems((range) =>
      ProjectsApi.getList(brandId, {
        range,
        order: { updatedAt: "desc" },
      }),
    );
  } finally {
    isLoadingProjects.value = false;
  }
}

watch(
  isOpen,
  async (open) => {
    if (open) {
      await loadProjects();
    } else {
      resetForm();
    }
  },
  { immediate: true },
);

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

const onSubmit = handleSubmit(async (values) => {
  await router.push({
    name: "CreateUmbrellaCampaign",
    params: { projectId: values.projectId },
  });
});
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
      {{ $t("brands.home.go-to-umbrella-campaign-modal.title") }}

      <template #description>
        {{ $t("brands.home.go-to-umbrella-campaign-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldAutocomplete
        name="projectId"
        leftIcon="tabler:search"
        :placeholder="
          $t('brands.home.go-to-umbrella-campaign-modal.select-placeholder')
        "
        :options="projectOptions"
        :loading="isLoadingProjects"
      />
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" type="button" @click="close">
        {{ $t("global.cancel") }}
      </Button>

      <Button type="submit" :isLoading="isSubmitting">
        {{ $t("brands.home.go-to-umbrella-campaign-modal.submit") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
