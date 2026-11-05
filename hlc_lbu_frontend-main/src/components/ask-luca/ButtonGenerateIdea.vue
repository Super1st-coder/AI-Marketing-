<script setup lang="ts" generic="T">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

interface CommonProps {
  textLabel?: string;
  textPlaceholder?: string;
  textMaxCharacters?: number;
  square?: boolean;
}

interface Props extends CommonProps {
  fetcher: () => Promise<T> | T;
  useText?: false;
}

interface PropsWithModal extends CommonProps {
  fetcher: (text: string) => Promise<T> | T;
  useText?: true;
}

const props = defineProps<Props | PropsWithModal>();

defineOptions({
  inheritAttrs: false,
});

const isModalOpen = ref(false);
const displayError = ref(false);

const emit = defineEmits<{
  generated: [data: T];
}>();

const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: toTypedSchema(
    object().shape({
      text: string().required(),
    }),
  ),
});

const onSubmit = handleSubmit(async (values) => {
  try {
    displayError.value = false;

    if (props.useText) {
      const generatedData = await props.fetcher(values.text);
      emit("generated", generatedData);
    }
  } catch (error) {
    displayError.value = true;
  } finally {
    isModalOpen.value = false;
  }
});

const isLoading = ref(false);
const handleClick = async () => {
  try {
    displayError.value = false;

    if (props.useText) {
      isModalOpen.value = true;
    } else {
      isLoading.value = true;

      let generatedData = await props.fetcher();
      emit("generated", generatedData);
    }
  } catch (error) {
    displayError.value = true;
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-2">
    <Button
      v-if="square"
      type="button"
      leftIcon="custom:hi-luca"
      @click="handleClick"
      :isLoading="isLoading"
      :square="square"
      v-bind="$attrs"
    />
    <Button
      v-else
      type="button"
      leftIcon="custom:hi-luca"
      @click="handleClick"
      :isLoading="isLoading"
      v-bind="$attrs"
    >
      <slot>
        {{ $t("global.ask-luca") }}
      </slot>
    </Button>

    <Alert v-if="displayError" type="error" autoScroll>
      {{ $t("forms.give-me-ideas.error-try-again") }}
    </Alert>

    <Modal
      v-model="isModalOpen"
      closeButton
      :maxWidth="1050"
      as="form"
      @submit.prevent="onSubmit"
    >
      <ModalHeader>
        <slot name="title">
          {{ $t("forms.give-me-ideas.modal-title") }}
        </slot>

        <template #description>
          <slot name="description">
            {{ $t("forms.give-me-ideas.modal-description") }}
          </slot>
        </template>
      </ModalHeader>

      <ModalBody>
        <FieldTextarea
          name="text"
          :label="textLabel"
          :placeholder="textPlaceholder"
          speechRecognition
          required
          class="tw:mb-[88px]"
          :maxCharacters="textMaxCharacters"
        />
      </ModalBody>

      <ModalFooter>
        <Button
          color="secondary"
          variant="outlined"
          type="button"
          @click="isModalOpen = false"
        >
          {{ $t("global.cancel") }}
        </Button>

        <Button type="submit" :isLoading="isSubmitting">
          <slot name="submit">
            {{ $t("global.generate") }}
          </slot>
        </Button>
      </ModalFooter>
    </Modal>
  </div>
</template>
