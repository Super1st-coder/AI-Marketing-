<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import type {
  AdsExperimentCreateCategoryData,
  AdsExperimentType,
} from "@/services/funnel-flow/paid-social/AdsExperiment";
import AdsExperiment from "@/services/funnel-flow/paid-social/AdsExperiment";

const props = defineProps<{
  format: AdsExperimentType;
}>();

const emit = defineEmits<{
  categoryCreated: [category: AdsExperimentCreateCategoryData];
}>();

const { t } = useI18n();
const brandId = useBrandId();
const isOpen = defineModel<boolean>({ required: true });

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string().required(t("forms.required-field")),
      description: string().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, resetForm, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
});

const onSubmit = handleSubmit(async (values) => {
  const response = await AdsExperiment.createExperimentCategory(brandId, {
    name: values.name,
    description: values.description,
    type: props.format,
  });

  emit("categoryCreated", response.data);
  isOpen.value = false;
  resetForm();
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
      {{
        $t("funnel-flow.paid-social.creative-angle.add-category-modal.title")
      }}
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldText
          name="name"
          :label="
            $t(
              'funnel-flow.paid-social.creative-angle.add-category-modal.name-label',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.creative-angle.add-category-modal.name-placeholder',
            )
          "
          required
        />

        <FieldTextarea
          name="description"
          :label="
            $t(
              'funnel-flow.paid-social.creative-angle.add-category-modal.description-label',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.creative-angle.add-category-modal.description-placeholder',
            )
          "
          required
        />
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" @click="close" type="button">
        {{ $t("global.cancel") }}
      </Button>

      <Button :isLoading="isSubmitting" type="submit">
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.add-category-modal.add-category",
          )
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
