<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import AdsExperiment from "@/services/funnel-flow/paid-social/AdsExperiment";

const props = defineProps<{
  categoryId: number;
}>();

const emit = defineEmits<{
  subcategoryCreated: [name: string];
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
  await AdsExperiment.createExperimentSubcategory(
    brandId,
    props.categoryId,
    values.name,
    values.description,
  );

  emit("subcategoryCreated", values.name);
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
        $t("funnel-flow.paid-social.creative-angle.add-subcategory-modal.title")
      }}
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldText
          name="name"
          :label="
            $t(
              'funnel-flow.paid-social.creative-angle.add-subcategory-modal.name-label',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.creative-angle.add-subcategory-modal.name-placeholder',
            )
          "
          required
        />

        <FieldTextarea
          name="description"
          :label="
            $t(
              'funnel-flow.paid-social.creative-angle.add-subcategory-modal.description-label',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.creative-angle.add-subcategory-modal.description-placeholder',
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
            "funnel-flow.paid-social.creative-angle.add-subcategory-modal.add-custom-variable",
          )
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
