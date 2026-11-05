<script lang="ts">
import { ButtonProps } from "@/components/buttons/base/Button.vue";
import ImageGenerationAPI from "@/services/ImageGenerationAPI";
import { useField } from "vee-validate";
import { ButtonHTMLAttributes } from "vue";
import { object, string, InferType, mixed, array, bool, number } from "yup";

export const imageGenerationSchema = object()
  .shape({
    isLoading: bool(),
    prompts: array().of(string().required()),
    selectedPrompt: string(),
    selectedPromptIndex: number(),
    generatedImage: mixed<Blob | string>(),
  })
  .optional();

export type ImageGeneration = InferType<typeof imageGenerationSchema>;

export type ImageGeneratorFetcher = () => Promise<string[]> | string[];
</script>

<script lang="ts" setup>
interface Props {
  name: string;
  selected?: boolean;
  useSubmitButton?: boolean;
  submitButtonProps?: ButtonHTMLAttributes & ButtonProps & { label?: string };
  editablePrompts?: boolean;
  promptFetcher?: ImageGeneratorFetcher;
  disabled?: boolean;
}

const props = defineProps<Props>();

const { t, te } = useI18n();

const abortController = ref<AbortController | undefined>();

const { setValue: setValues } = useField<ImageGeneration>(() => props.name);
const promptGenerationErrorMessage = ref<string>();

const { value: prompts, setValue: setPrompts } = useField<string[] | undefined>(
  () => `${props.name}.prompts`,
);

const { value: isLoading, setValue: setIsLoading } = useField<
  boolean | undefined
>(() => `${props.name}.isLoading`);

const { value: selectedPrompt, setValue: setSelectedPrompt } = useField<
  string | undefined
>(() => `${props.name}.selectedPrompt`);

const { value: selectedPromptIndex, setValue: setSelectedPromptIndex } =
  useField<number | undefined>(() => `${props.name}.selectedPromptIndex`);

const { value: generatedImage, setValue: setGeneratedImage } = useField<
  Blob | string | undefined
>(() => `${props.name}.generatedImage`);

// Handle both File objects and string URLs
const generatedImageUrl = useObjectOrStringUrl(() => generatedImage.value);
const promptCount = computed(() => prompts.value?.length ?? 0);
const imageErrorMessage = ref<string | undefined>(undefined);

const emit = defineEmits<{
  generatePrompts: [];
}>();

const handleGeneratePrompts = async () => {
  if (props.promptFetcher) {
    try {
      // Set loading
      setIsLoading(true);
      promptGenerationErrorMessage.value = undefined;

      // Generate prompts
      const prompts = await props.promptFetcher();

      // Save prompts
      setIsLoading(false);
      setPrompts(prompts);
    } catch (error) {
      if (error instanceof Error) {
        promptGenerationErrorMessage.value = te(`errors.${error.message}.title`)
          ? t(`errors.${error.message}.title`)
          : error.message;
        setIsLoading(false);
      } else {
        throw error;
      }
    }
  } else {
    emit("generatePrompts");
  }
};

const handleSelectPrompt = (prompt: string, index: number) => {
  setSelectedPrompt(prompt);
  setSelectedPromptIndex(index);
  generateImage();
};

const editedPrompt = computed<string>({
  get: () => {
    if (selectedPrompt.value && selectedPromptIndex.value != undefined) {
      return selectedPrompt.value;
    }

    return "";
  },
  set: (value) => {
    if (prompts.value && selectedPrompt.value) {
      selectedPrompt.value = value;
      setPrompts(
        prompts.value.map((prompt, index) =>
          index === selectedPromptIndex.value ? value : prompt,
        ),
      );
    }
  },
});

const generateImage = async () => {
  setIsLoading(true);

  try {
    imageErrorMessage.value = undefined;

    // Fetch the image
    abortController.value = new AbortController();
    const image = await ImageGenerationAPI.generate(
      selectedPrompt.value ?? "",
      abortController.value.signal,
    );

    if (image.size === 0) {
      throw new Error("The image is empty.");
    }

    // Set the new image
    setGeneratedImage(image);
    setIsLoading(false);
  } catch (error) {
    await sleep(1000);

    console.log(error);
    imageErrorMessage.value =
      "There was a problem generating this image. Try another prompt.";
    setIsLoading(false);
  }
};

const handleGoBack = () => {
  abortController.value?.abort();
  setSelectedPrompt(undefined);
  setSelectedPromptIndex(undefined);
  setGeneratedImage(undefined);

  imageErrorMessage.value = undefined;
};

const handleGoBeforeGeneration = () => {
  setValues({ prompts: [] });
};
</script>

<template>
  <div v-if="selectedPrompt" class="tw:flex tw:flex-col tw:gap-6 tw:lg:gap-12">
    <div class="tw:flex tw:justify-between">
      <Button
        variant="outlined"
        color="primary"
        leftIcon="tabler-arrow-left"
        type="button"
        size="lg"
        @click="handleGoBack"
        :disabled="disabled"
      >
        {{ $t("image-generator.buttonbackprompt") }}
      </Button>
    </div>

    <div>
      <div
        class="tw:relative tw:mb-8 tw:overflow-hidden tw:rounded-md tw:shadow-xl"
      >
        <img
          v-if="generatedImageUrl"
          :src="generatedImageUrl"
          class="tw:aspect-square tw:w-full tw:object-cover"
        />
        <div v-else class="tw:aspect-square tw:bg-input-border"></div>

        <div
          v-if="isLoading"
          class="tw:absolute tw:top-1/2 tw:left-1/2 tw:flex tw:-translate-x-1/2 tw:-translate-y-1/2"
        >
          <CircleLoader class="tw:text-5xl tw:text-white" />
        </div>
      </div>

      <FieldBaseEditableText
        v-if="editablePrompts"
        v-model="editedPrompt"
        type="textarea"
        :disabled="disabled"
      />
      <p v-else class="tw:rounded-md tw:bg-white tw:px-4 tw:py-2">
        {{ selectedPrompt }}
      </p>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-4">
      <Alert v-if="imageErrorMessage" type="error">
        {{ imageErrorMessage }}
      </Alert>

      <div
        class="tw:flex tw:flex-col tw:justify-between tw:gap-2 tw:lg:flex-row"
      >
        <Button
          size="lg"
          @click="generateImage"
          variant="outlined"
          type="button"
          color="primary"
          :disabled="disabled || isLoading || submitButtonProps?.isLoading"
        >
          {{ $t("image-generator.regenerate-image") }}
        </Button>

        <Button
          v-if="useSubmitButton"
          size="lg"
          type="submit"
          v-bind="submitButtonProps"
          :color="submitButtonProps?.color ?? 'primary'"
          :disabled="
            disabled ||
            isLoading ||
            !generatedImage ||
            submitButtonProps?.isLoading
          "
        >
          {{ submitButtonProps?.label ?? $t("image-generator.select-image") }}
        </Button>

        <slot name="submitButton" v-bind="{ isLoading }" />
      </div>
    </div>
  </div>
  <div v-else-if="promptCount > 0">
    <div class="tw:mb-8 tw:flex tw:items-center tw:justify-between">
      <ButtonGoBack
        size="lg"
        @click="handleGoBeforeGeneration"
        :disabled="disabled"
      />

      <h3 class="tw:text-lg tw:font-extrabold">
        {{ $t("image-generator.image-generation-prompts") }}
      </h3>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-3">
      <button
        v-for="(prompt, index) in prompts"
        class="tw:rounded-md tw:border tw:border-secondary/16 tw:bg-white tw:p-6 tw:text-left tw:text-sm tw:hover:border-transparent tw:hover:bg-primary/8"
        :class="{ 'tw:pointer-events-none tw:opacity-50': disabled }"
        @click="handleSelectPrompt(prompt, index)"
        :disabled="disabled"
      >
        {{ prompt }}
      </button>
    </div>
  </div>
  <div
    v-else
    class="tw:flex tw:flex-col tw:items-center tw:justify-center tw:gap-8"
  >
    <Icon icon="tabler-photo" class="tw:text-[60px]" />
    <div class="tw:text-center">
      <h3 class="tw:mb-5 tw:text-lg tw:font-extrabold">
        <slot name="title" />
      </h3>

      <p>
        <slot name="description" />
      </p>
    </div>

    <Alert v-if="promptGenerationErrorMessage" type="error">
      {{ promptGenerationErrorMessage }}
    </Alert>

    <Button
      type="button"
      @click="handleGeneratePrompts"
      :isLoading="isLoading"
      size="lg"
      :disabled="disabled"
    >
      {{ $t("image-generator.generate") }}
    </Button>
  </div>
</template>
