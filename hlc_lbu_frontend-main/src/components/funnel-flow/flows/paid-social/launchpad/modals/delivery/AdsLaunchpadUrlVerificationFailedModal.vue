<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { computed, ref, watch } from "vue";

const props = defineProps<{
  creativeId: number;
  // The summary shows the checks without allowing changes
  readonly?: boolean;
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

// Error message from API
const generalErrorMessage = ref<string | undefined>(undefined);

// Schema
const schema = computed(() =>
  toTypedSchema(
    object({
      url: string()
        .required(t("forms.required-field"))
        .url(t("forms.url-invalid")),
    }),
  ),
);

const { handleSubmit, meta, values, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    url: preCheckStore.getProposalUrl(props.creativeId),
  },
});

// Clear API error when user changes the form value
watch(
  () => values.url,
  () => {
    if (generalErrorMessage.value) {
      generalErrorMessage.value = undefined;
    }
  },
);

const onSubmit = handleSubmit(async (values) => {
  if (props.readonly) {
    return;
  }

  try {
    await preCheckStore.setProposalUrl(props.creativeId, values.url);

    isOpen.value = false;
  } catch (error: any) {
    const errorCode = error?.message?.code;

    if (errorCode) {
      generalErrorMessage.value =
        error?.message?.message ||
        t("funnel-flow.paid-social.launchpad.url-modal.errors.generic");
    } else {
      throw error;
    }
  }
});

const handleCancel = () => {
  isOpen.value = false;
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    useCustomClose
    @customClose="handleCancel"
    alignment="top"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.launchpad.url-modal.title") }}

      <template #description>
        {{ $t("funnel-flow.paid-social.launchpad.url-modal.description") }}
      </template>

      <template #after>
        <Alert v-if="generalErrorMessage" type="error" class="tw:mt-6">
          <strong>
            {{ $t("funnel-flow.paid-social.launchpad.url-modal.error-prefix") }}
          </strong>
          {{ generalErrorMessage }}
        </Alert>
        <Alert
          v-else
          :type="meta.valid ? 'success' : 'warning'"
          class="tw:mt-6"
        >
          <template v-if="meta.valid">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.url-modal.validation.passed",
              )
            }}
          </template>
          <template v-else>
            <strong>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.url-modal.validation.action-required-prefix",
                )
              }}
            </strong>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.url-modal.validation.action-required-message",
              )
            }}
          </template>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldText
        name="url"
        :disabled="readonly"
        :placeholder="
          $t(
            'funnel-flow.paid-social.launchpad.url-modal.fields.url-placeholder',
          )
        "
      />
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        @click="handleCancel"
      >
        {{ $t("global.close") }}
      </Button>

      <Button
        v-if="!readonly"
        type="submit"
        :disabled="!meta.valid"
        :isLoading="isSubmitting"
      >
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
