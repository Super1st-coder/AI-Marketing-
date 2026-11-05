<script setup lang="ts">
import { ButtonProps } from "../buttons/base/Button.vue";
import { ModalProps } from "./base/Modal.vue";

export type ModalGenericConfirmFn = () => Promise<void | boolean> | void;

export interface ModalGenericProps extends Pick<
  ModalProps,
  "closeButton" | "closeOnClickOutside" | "scrollable"
> {
  name?: string;
  imageSrc?: string;
  icon?: string;
  /** Displays the video player. A placeholder is shown while `videoSrc` is missing. */
  displayVideo?: boolean;
  videoSrc?: string;
  displayShowCheckbox?: boolean;
  maxWidth?: string | number;
  /** `default` uses header/body/footer; `centered` stacks title, body, and actions. */
  variant?: "default" | "centered";
  /**
   * Renders the modal as a `<form>`. Submitting it (the Continue button or
   * Enter in an input) goes through the same confirm flow as clicking Continue.
   */
  as?: "div" | "form";

  /** Extra props forwarded to the cancel button. */
  cancelButtonProps?: ButtonProps;
  /** Extra props forwarded to the continue button. */
  continueButtonProps?: ButtonProps;

  /**
   * Runs when Continue is clicked. The modal stays open while it is pending
   * and closes afterward, unless it returns `false`.
   * If omitted, the `confirm` event is emitted instead.
   */
  confirmFn?: ModalGenericConfirmFn;
}

const props = withDefaults(defineProps<ModalGenericProps>(), {
  closeButton: true,
  closeOnClickOutside: true,
  maxWidth: 660,
  variant: "default",
  as: "div",
});

const isOpen = defineModel<boolean>({ required: true });
const dontShowAgain = defineModel<boolean>("dontShowAgain", {
  required: false,
});
const isConfirming = ref(false);

const emit = defineEmits(["confirm", "cancel", "close"]);

const handleConfirm = async () => {
  // A form can be submitted again with Enter while a confirm is still running
  if (isConfirming.value) return;

  if (props.confirmFn) {
    isConfirming.value = true;
    const result = await props.confirmFn();
    isConfirming.value = false;

    if (result === false) {
      return;
    }
  } else {
    emit("confirm");
  }

  isOpen.value = false;
};

const handleCancel = () => {
  emit("cancel");
  isOpen.value = false;
};

const handleClose = () => {
  emit("close");
  isOpen.value = false;
};

const checkboxId = computed(() => `dontShowAgain-${props.name}`);

const isForm = computed(() => props.as === "form");

// In a form, Continue is a submit button and the `submit` event confirms,
// so the click itself must not confirm too
const handleContinueClick = () => {
  if (!isForm.value) {
    handleConfirm();
  }
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="maxWidth"
    :closeButton="isConfirming ? false : closeButton"
    :closeOnClickOutside="isConfirming ? false : closeOnClickOutside"
    useCustomClose
    :scrollable="scrollable"
    :as="as"
    @customClose="handleClose"
    @submit.prevent="handleConfirm"
  >
    <template v-if="variant === 'default'">
      <ModalHeader v-if="$slots.title || $slots.description">
        <slot name="title" />

        <template v-if="$slots.description" #description>
          <slot name="description" />
        </template>
      </ModalHeader>

      <ModalBody class="tw:flex tw:flex-col tw:gap-6">
        <div
          v-if="$slots.before || imageSrc || icon"
          class="tw:flex tw:flex-col tw:items-center tw:gap-3 tw:text-center"
        >
          <slot name="before" />

          <img v-if="imageSrc" :src="imageSrc" class="tw:max-h-[120px]" />

          <Icon
            v-if="icon"
            :icon="icon"
            class="tw:text-[120px] tw:text-primary"
          />
        </div>

        <VideoPlayer v-if="displayVideo || videoSrc" :src="videoSrc" />

        <slot />

        <FieldBaseCheckbox
          v-if="displayShowCheckbox"
          v-model="dontShowAgain"
          :name="checkboxId"
          :label="$t('global.dont-show-this-message-again')"
          class="tw:justify-center"
        />
      </ModalBody>

      <ModalFooter
        v-if="
          $slots.footerBefore ||
          $slots.continue ||
          $slots.cancel ||
          $slots.actions
        "
      >
        <template v-if="$slots.footerBefore" #before>
          <slot name="footerBefore" />
        </template>

        <Button
          v-if="$slots.cancel"
          color="secondary"
          variant="outlined"
          @click="handleCancel"
          type="button"
          :disabled="isConfirming"
          v-bind="cancelButtonProps"
        >
          <slot name="cancel" />
        </Button>

        <Button
          v-if="$slots.continue"
          :type="isForm ? 'submit' : 'button'"
          @click="handleContinueClick"
          :isLoading="isConfirming"
          v-bind="continueButtonProps"
        >
          <slot name="continue" />
        </Button>

        <slot
          name="actions"
          :cancel="handleCancel"
          :close="handleClose"
          :confirm="handleConfirm"
        />
      </ModalFooter>
    </template>

    <div
      v-else-if="variant === 'centered'"
      class="tw:flex tw:flex-col tw:items-center tw:gap-3 tw:p-8 tw:text-center"
    >
      <slot name="before" />

      <img v-if="imageSrc" :src="imageSrc" class="tw:max-h-[120px]" />

      <Icon v-if="icon" :icon="icon" class="tw:text-[120px] tw:text-primary" />

      <h2
        v-if="variant === 'centered' && $slots.title"
        class="tw:text-3xl tw:font-bold tw:whitespace-pre-line"
      >
        <slot name="title" />
      </h2>

      <p
        v-if="variant === 'centered' && $slots.description"
        class="tw:font-medium tw:whitespace-pre-line tw:text-secondary-text"
      >
        <slot name="description" />
      </p>

      <VideoPlayer
        v-if="displayVideo || videoSrc"
        :src="videoSrc"
        class="tw:mt-3"
      />

      <slot />

      <FieldBaseCheckbox
        v-if="displayShowCheckbox"
        v-model="dontShowAgain"
        :name="checkboxId"
        :label="$t('global.dont-show-this-message-again')"
        class="tw:mt-6 tw:justify-center"
      />

      <div
        v-if="$slots.continue || $slots.cancel || $slots.actions"
        class="tw:md:flex- tw:mt-5 tw:flex tw:w-full tw:flex-col-reverse tw:items-center tw:gap-3 tw:md:flex-row tw:md:justify-center"
        :class="{
          'tw:*:grow tw:*:basis-0':
            ($slots.continue && $slots.cancel) || $slots.actions,
        }"
      >
        <Button
          v-if="$slots.cancel"
          color="secondary"
          variant="outlined"
          @click="handleCancel"
          type="button"
          :disabled="isConfirming"
          v-bind="cancelButtonProps"
        >
          <slot name="cancel" />
        </Button>

        <Button
          v-if="$slots.continue"
          :type="isForm ? 'submit' : 'button'"
          @click="handleContinueClick"
          :isLoading="isConfirming"
          v-bind="continueButtonProps"
        >
          <slot name="continue" />
        </Button>

        <slot
          name="actions"
          :cancel="handleCancel"
          :close="handleClose"
          :confirm="handleConfirm"
        />
      </div>
    </div>
  </Modal>
</template>
