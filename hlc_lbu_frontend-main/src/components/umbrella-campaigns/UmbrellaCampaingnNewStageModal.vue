<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { useForm } from "vee-validate";
import { watch, nextTick } from "vue";

const isOpen = defineModel<boolean>({ required: true });

const emit = defineEmits(["add-stage", "close"]);

const { t } = useI18n();

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string()
        .required("Custom Stage Name is required")
        .max(100, ({ max }) => t("forms.max-characters", { max })),
      context: string().max(250, ({ max }) =>
        t("forms.max-characters", { max }),
      ),
    }),
  ),
);

const { handleSubmit, isSubmitting, errors, resetForm } = useForm({
  validationSchema: schema,
  initialValues: {
    name: "",
    context: "",
  },
});

// Resetear el formulario cuando se abre el modal
watch(isOpen, (newValue) => {
  if (newValue) {
    nextTick(() => {
      resetForm();
    });
  }
});

const onSubmit = handleSubmit(async (formValues) => {
  try {
    emit("add-stage", {
      name: formValues.name,
      display_name: formValues.name,
      context: formValues.context,
    });

    // Cerrar el modal y resetear el formulario
    isOpen.value = false;
    resetForm();
  } catch (error) {
    console.error("Error adding stage:", error);
  }
});

function handleCancel() {
  isOpen.value = false;
  resetForm();
  emit("close");
}
</script>

<template>
  <Modal
    v-model="isOpen"
    class="tw:w-[850px] tw:max-w-[850px] tw:rounded-[30px] tw:px-[30px] tw:pt-[24px] tw:pb-[24px]"
    closeButton
    style="height: 529px"
  >
    <PageTitle
      helpButton
      is="h2"
      class="tw:mb-[38px]"
      helpVideoUrl="https://www.youtube.com/watch?v=h3RLoihDatg"
    >
      {{ $t("umbrella-campaign.step-scene.stages.modal-addstage.title") }}
    </PageTitle>
    <form @submit.prevent="onSubmit">
      <div class="tw:mb-6">
        <FieldTextarea
          name="name"
          :label="
            $t('umbrella-campaign.step-scene.stages.modal-addstage.name-label')
          "
          :placeholder="
            $t(
              'umbrella-campaign.step-scene.stages.modal-addstage.name-placeholder',
            )
          "
          required
          :maxCharacters="100"
          :rows="1"
        />
        <div v-if="errors.name" class="tw:text-red-500 tw:mt-1 tw:text-xs">
          <span v-if="errors.name === 'Custom Stage Name is required'">
            {{
              $t(
                "umbrella-campaign.step-scene.stages.modal-addstage.name-required",
              )
            }}
          </span>
          <span v-else-if="errors.name === 'Max 100 characters'">
            {{
              $t("umbrella-campaign.step-scene.stages.modal-addstage.name-max")
            }}
          </span>
          <span v-else>{{ errors.name }}</span>
        </div>
      </div>
      <div class="tw:mb-2">
        <FieldTextarea
          name="context"
          :label="
            $t(
              'umbrella-campaign.step-scene.stages.modal-addstage.context-label',
            )
          "
          :placeholder="
            $t(
              'umbrella-campaign.step-scene.stages.modal-addstage.context-placeholder',
            )
          "
          :maxCharacters="250"
          :rows="3"
        />
        <div class="tw:mt-1 tw:text-xs tw:text-gray-500">
          {{
            $t("umbrella-campaign.step-scene.stages.modal-addstage.context-max")
          }}
        </div>
      </div>
      <div class="tw:mt-8 tw:flex tw:justify-between">
        <ButtonGoBack
          class="tw:basis-[260px]"
          type="button"
          @click="handleCancel"
        >
          {{ $t("global.cancel") }}
        </ButtonGoBack>
        <Button
          class="tw:basis-[260px]"
          type="submit"
          :isLoading="isSubmitting"
        >
          {{ $t("umbrella-campaign.step-scene.stages.modal-addstage.add") }}
        </Button>
      </div>
    </form>
  </Modal>
</template>
