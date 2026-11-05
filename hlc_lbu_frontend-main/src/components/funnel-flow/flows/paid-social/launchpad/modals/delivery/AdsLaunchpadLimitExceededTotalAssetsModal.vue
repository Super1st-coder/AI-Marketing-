<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });

const handleSave = () => {
  isOpen.value = false;
};

const handleCancel = () => {
  isOpen.value = false;
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="865"
    closeButton
    useCustomClose
    @customClose="handleCancel"
    alignment="top"
  >
    <ModalHeader>
      {{
        $t("funnel-flow.paid-social.launchpad.limit-total-assets-modal.title")
      }}

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.limit-total-assets-modal.description",
          )
        }}
      </template>

      <template #after>
        <Alert type="warning" class="tw:mt-6">
          <strong>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.limit-total-assets-modal.validation.action-required-prefix",
              )
            }}
          </strong>
          {{
            $t(
              "funnel-flow.paid-social.launchpad.limit-total-assets-modal.validation.action-required-message",
            )
          }}
          {{ " " }}
          <span v-pre>{{ count }}</span> asset(s) from any category to proceed.
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <p>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.limit-total-assets-modal.body-placeholder",
          )
        }}
      </p>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        @click="handleCancel"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button type="button" @click="handleSave">
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
