<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { useForm } from "vee-validate";
import { watch, nextTick } from "vue";

const isOpen = defineModel<boolean>({ required: true });

const props = defineProps<{
  name: string;
  display_name: string;
  avatar?: string;
  context?: string;
  text?: string;
}>();

const emit = defineEmits(["save-context", "close"]);

const { t } = useI18n();

const schema = computed(() =>
  toTypedSchema(
    object({
      context: string().max(250, ({ max }) =>
        t("forms.max-characters", { max }),
      ),
    }),
  ),
);

const { handleSubmit, isSubmitting, setFieldValue } = useForm({
  validationSchema: schema,
  initialValues: {
    context: "",
  },
});

// Inicializar el contexto cuando se abra el modal
watch(isOpen, (newValue) => {
  if (newValue) {
    nextTick(() => {
      const initialContext = props.text || props.context || "";
      setFieldValue("context", initialContext);
    });
  }
});

// También watch para cambios en props
watch(
  () => [props.context, props.text],
  () => {
    if (isOpen.value) {
      const initialContext = props.text || props.context || "";
      setFieldValue("context", initialContext);
    }
  },
  { immediate: true },
);

const onSubmit = handleSubmit(async (formValues) => {
  try {
    emit("save-context", {
      name: props.name,
      context: formValues.context,
    });
    isOpen.value = false;
  } catch (error) {
    console.error("Error saving context:", error);
  }
});

function handleCancel() {
  isOpen.value = false;
  emit("close");
}
</script>

<template>
  <Modal
    v-model="isOpen"
    class="tw:w-[1050px] tw:max-w-[1050px] tw:rounded-[30px] tw:px-[40px] tw:pt-[24px] tw:pb-[24px]"
    closeButton
    style="height: 425px"
  >
    <PageTitle
      helpButton
      is="h2"
      class="tw:mb-[24px] tw:flex tw:items-center tw:gap-2"
      helpVideoUrl="https://www.youtube.com/watch?v=h3RLoihDatg"
    >
      {{ $t("umbrella-campaign.step-scene.stages.modal-contextstage.title") }}
    </PageTitle>

    <div class="tw:mb-4 tw:text-lg tw:font-semibold">
      {{
        $t("umbrella-campaign.step-scene.stages.modal-contextstage.subtitle")
      }}
    </div>

    <form @submit.prevent="onSubmit">
      <FieldTextarea
        name="context"
        :label="
          $t(
            'umbrella-campaign.step-scene.stages.modal-contextstage.context-label',
          )
        "
        :placeholder="
          $t(
            'umbrella-campaign.step-scene.stages.modal-contextstage.context-placeholder',
          )
        "
        :maxCharacters="250"
        :rows="3"
        :maxVisibleLines="4"
        characterCounterPosition="end"
      />

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
          {{
            $t("umbrella-campaign.step-scene.stages.modal-contextstage.save")
          }}
        </Button>
      </div>
    </form>
  </Modal>
</template>
