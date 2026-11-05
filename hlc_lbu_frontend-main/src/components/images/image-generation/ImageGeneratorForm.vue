<script lang="ts">
export type ImageGeneratorFormInitialAttributesObject<U extends string> =
  Record<U, string | undefined>;
export type ImageGeneratorFormAttributesObject<U extends string> = Record<
  U,
  string
>;

export type ImageGeneratorFormInput<T extends string> = {
  attributes?: ImageGeneratorFormInitialAttributesObject<T>;
  prompts?: ImagePrompt[] | ImagePrompt2[] | null | undefined;
  selectedPrompt?: ImagePrompt | ImagePrompt2 | null;
  image?: Blob | string | null;
};

export type ImageGeneratorFormOutput<T extends string> = {
  selectedPrompt: string;
  selectedPromptIndex: number;
  generatedImage: string | Blob;
  attributes: ImageGeneratorFormAttributesObject<T>;
};
</script>

<script setup lang="ts" generic="T extends string">
import { toTypedSchema } from "@vee-validate/yup";
import { array, object, string } from "yup";
import {
  imageGenerationSchema,
  ImageGeneratorFetcher,
} from "./ImageGenerator.vue";
import {
  ImageRequiredAttributesEmpty,
  UnidentifiedError,
} from "@/services/common-errors";
import ImageGenerationAPI from "@/services/ImageGenerationAPI";
import { IconCardVariant } from "@/components/cards/IconCard.vue";

const emit = defineEmits<{
  goNext: [];
}>();

const props = defineProps<{
  attributes: Readonly<T[]>;
  initialValues?: ImageGeneratorFormInput<T>;
  regenerateAttributesFn: () => Promise<
    ImageGeneratorFormInitialAttributesObject<T>
  >;
  generatePromptsFn: (
    attributes: ImageGeneratorFormAttributesObject<T>,
  ) => Promise<string[]>;
  selectImageFn: (values: ImageGeneratorFormOutput<T>) => void;
}>();

const { t } = useI18n();

const schema = computed(() =>
  toTypedSchema(
    object({
      attributes: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            value: string().required(),
          }),
        )
        .required(),
      imageGeneration: imageGenerationSchema,
    }),
  ),
);

function convertAttributesObjectToArray(
  attributes: ImageGeneratorFormInitialAttributesObject<T> | undefined,
) {
  return props.attributes.map<{ name: T; value: string }>((attributeName) => {
    const foundAttributeValue = attributes?.[attributeName];

    if (foundAttributeValue) {
      return {
        name: attributeName,
        value: foundAttributeValue,
      };
    }

    return {
      name: attributeName,
      value: "",
    };
  });
}

const initialAttributes = convertAttributesObjectToArray(
  props.initialValues?.attributes,
);

const { handleSubmit, values, isSubmitting, resetForm, meta } =
  useFormWithErrorScrolling({
    validateOnMount: true,
    validationSchema: schema,
    initialValues: {
      attributes: initialAttributes,
      // Only display the prompts if the attributes have been saved
      imageGeneration: ImageGenerationAPI.mapDataToSchema(
        props.initialValues?.prompts,
        props.initialValues?.selectedPrompt,
        props.initialValues?.image,
      ),
    },
  });

const onSubmit = handleSubmit(async (values) => {
  if (
    !values.imageGeneration ||
    !values.imageGeneration.generatedImage ||
    !values.imageGeneration.selectedPrompt ||
    values.imageGeneration.selectedPromptIndex === undefined
  ) {
    throw new UnidentifiedError();
  }

  await props.selectImageFn({
    attributes: getAttributesObject(),
    selectedPromptIndex: values.imageGeneration.selectedPromptIndex,
    selectedPrompt: values.imageGeneration.selectedPrompt,
    generatedImage: values.imageGeneration.generatedImage,
  });
});

function getAttributesObject(): ImageGeneratorFormAttributesObject<T> {
  const hola =
    props.attributes.reduce<ImageGeneratorFormAttributesObject<T>>(
      (accumulator, currentValue) => {
        const foundAttribute = values.attributes?.find(
          (attribute) => attribute.name === currentValue,
        );

        accumulator[currentValue as string] = foundAttribute?.value ?? "";
        return accumulator;
      },
      {} as ImageGeneratorFormAttributesObject<T>,
    ) ?? {};

  return hola;
}

const handleGeneratePrompts: ImageGeneratorFetcher = async () => {
  if (values.attributes?.some((attribute) => !attribute)) {
    throw new ImageRequiredAttributesEmpty();
  }

  const attributes = getAttributesObject();

  // Generate prompts
  return await props.generatePromptsFn(attributes);
};

const displayBadGenerationWarning = computed(() => {
  return (
    // If some generated attributes are missing
    values.attributes?.some((attribute) => !attribute.value)
  );
});

const isRegenerating = ref(false);

async function handleRegenerateAttributes() {
  isRegenerating.value = true;
  const response = await props.regenerateAttributesFn();

  resetForm({
    values: { attributes: convertAttributesObjectToArray(response) },
  });

  isRegenerating.value = false;
}

const styles: Record<
  string,
  {
    icon?: string;
    iconVariant?: IconCardVariant;
  }
> = {
  core_idea: {
    icon: "tabler-bulb",
    iconVariant: "primary",
  },
  primary_visual: {
    icon: "tabler-eye",
    iconVariant: "info",
  },
  emotion: {
    icon: "tabler-mood-happy",
    iconVariant: "error",
  },
  place: {
    icon: "tabler-map",
    iconVariant: "success",
  },
  target_audience: {
    icon: "ic:round-people-alt",
    iconVariant: "primary",
  },
  physical_appearance: {
    icon: "tabler-shirt",
    iconVariant: "primary",
  },
  background: {
    icon: "tabler-mountain",
    iconVariant: "success",
  },
  activity_or_action: {
    icon: "tabler-run",
    iconVariant: "error",
  },
  objects_or_props: {
    icon: "tabler-eyeglass",
    iconVariant: "info",
  },
  expression_and_emotion: {
    icon: "tabler-mood-smile",
    iconVariant: "gray",
  },
};
</script>

<template>
  <form @submit.prevent="onSubmit">
    <div class="tw:flex tw:flex-col tw:gap-[30px] tw:lg:flex-row tw:lg:gap-10">
      <div class="tw:flex tw:basis-1/2 tw:flex-col tw:gap-12">
        <h2 class="tw:text-2xl tw:font-extrabold">
          <slot name="subtitle" />
        </h2>

        <Alert v-if="displayBadGenerationWarning" type="error">
          <slot name="alert-message" />
          <template #actions>
            <Button
              size="md"
              @click="handleRegenerateAttributes"
              :isLoading="isRegenerating"
            >
              <slot name="alert-regenerate" />
            </Button>
          </template>
        </Alert>

        <CardSections>
          <EditableCardSection
            v-for="(attribute, index) in attributes"
            :key="attribute"
            :name="`attributes.${index}.value`"
            :title="
              $te(`image-generator.attributes.${attribute}.label`)
                ? $t(`image-generator.attributes.${attribute}.label`)
                : attribute
            "
            :icon="styles[attribute]?.icon ?? 'tabler:cube'"
            :iconVariant="styles[attribute]?.iconVariant ?? 'gray'"
            editable
            required
          />
        </CardSections>
      </div>

      <div>
        <Separator type="vertical" class="tw:hidden tw:lg:block" />
        <Separator type="horizontal" class="tw:lg:hidden" />
      </div>

      <ImageGenerator
        name="imageGeneration"
        class="tw:basis-1/2 tw:self-start tw:py-16"
        :promptFetcher="handleGeneratePrompts"
        useSubmitButton
        :submitButtonProps="{ isLoading: isSubmitting }"
        editablePrompts
      >
        <template #title>
          <slot name="image-generator-title" />
        </template>
        <template #description>
          <slot name="image-generator-description" />
        </template>
      </ImageGenerator>
    </div>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </form>
</template>
