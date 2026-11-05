<script lang="ts">
import { imageGenerationSchema } from "@/components/images/image-generation/ImageGenerator.vue";
import { useField } from "vee-validate";
import { object, string, InferType, boolean, number } from "yup";

export const metaAdSchema = object().shape({
  selected: boolean(),
  id: number().required(),
  title: string().required(),
  context: string().required(),
  primaryText: string().required(),
  imageHook: string().required(),
  imagePunchline: string().required(),
  headline: string().required(),
  description: string(),
  cta: string().required(),
  imageGeneration: imageGenerationSchema,
});

export type MetaAd = InferType<typeof metaAdSchema>;
</script>

<script lang="ts" setup>
interface Props {
  name: string;
  selected?: boolean;
  brandName: string;
  projectId: number | string;
}

const props = defineProps<Props>();
const isOpen = ref(false);

const emit = defineEmits<{
  checked: [checked: boolean];
  generatePrompts: [];
}>();

const { value: model } = useField<MetaAd>(props.name, undefined);
const { value: isSelected } = useField<boolean>(
  `${props.name}.selected`,
  undefined,
);

const imageGenerationFieldName = computed(
  () => `${props.name}.imageGeneration`,
);

watch(isSelected, () => {
  emit("checked", isSelected.value);
});
</script>

<template>
  <SelectableCard v-model:selected="isSelected">
    <template #header>
      <CardTitle is="h2">
        {{ model.title }}
      </CardTitle>
    </template>

    <button
      class="tw:flex tw:flex-col tw:gap-5 tw:text-left"
      type="button"
      @click="isOpen = true"
    >
      <div
        :class="[
          'tw:mx-auto tw:w-full tw:max-w-[400px] tw:overflow-hidden tw:rounded-lg tw:bg-white',
          'tw:font-roboto tw:text-sm tw:text-[#050505] tw:shadow-[0px_1px_2px] tw:shadow-black/20',
        ]"
      >
        <div class="tw:p-4">
          <div class="tw:mb-2.5 tw:flex tw:gap-2">
            <div
              class="flex-center tw:h-[38px] tw:w-[38px] tw:shrink-0 tw:rounded-full tw:bg-secondary/16"
            >
              <Icon
                icon="tabler-box"
                class="tw:text-[22px] tw:text-secondary"
              />
            </div>

            <div class="tw:grow">
              <h3 class="tw:font-bold">{{ brandName }}</h3>
              <p class="tw:text-xs">Sponsored</p>
            </div>

            <Icon icon="tabler-dots" class="tw:text-[24px] tw:text-[#65676B]" />
          </div>

          <div>
            {{ model.primaryText }}
          </div>
        </div>

        <Separator />

        <ImageGeneratorPreview
          :name="imageGenerationFieldName"
          class="tw:aspect-280/416"
        >
          <template #before>
            <div
              class="tw:rounded tw:border tw:border-[#9E9E9E] tw:bg-white tw:px-3 tw:py-2"
            >
              {{ model.imageHook }}
            </div>
          </template>

          <template #after>
            <div
              class="tw:rounded tw:border tw:border-[#9E9E9E] tw:bg-white tw:px-3 tw:py-2"
            >
              {{ model.imagePunchline }}
            </div>
          </template>
        </ImageGeneratorPreview>

        <Separator />

        <div class="tw:flex tw:items-center tw:gap-2.5 tw:bg-[#F0F2F5] tw:p-4">
          <div>
            <h3 class="tw:text-base tw:font-bold">{{ model.headline }}</h3>
            <p v-if="model.description" class="tw:text-[#65676B]">
              {{ model.description }}
            </p>
          </div>

          <button
            class="tw:pointer-events-none tw:basis-3/4 tw:rounded-md tw:bg-[#E4E6EB] tw:px-3 tw:py-2.5 tw:font-bold tw:whitespace-nowrap"
            type="button"
          >
            {{ model.cta }}
          </button>
        </div>
      </div>
    </button>

    <ModalStandard v-model="isOpen">
      <template #header>
        <CardTitle is="h2"> {{ model.title }} </CardTitle>
        <CardParagraph variant="light">
          {{ model.context }}
        </CardParagraph>
      </template>

      <template #headerActions>
        <ButtonAskLuca class="tw:grow" />
        <ButtonCheck
          @click="isSelected = !isSelected"
          type="button"
          :checked="isSelected"
        />
      </template>

      <template #body>
        <div
          class="tw:flex tw:grow tw:flex-col tw:gap-8 tw:lg:shrink-0 tw:lg:basis-1/2"
        >
          <EditableCardSection
            :name="`${name}.primaryText`"
            title="Primary Text"
            icon="tabler-mist"
            iconVariant="primary"
            editable
          />

          <EditableCardSection
            :name="`${name}.imageHook`"
            title="Image Hook"
            icon="tabler-anchor"
            iconVariant="info"
            editable
          />

          <EditableCardSection
            :name="`${name}.imagePunchline`"
            title="Image Punchline"
            icon="tabler-flame"
            iconVariant="error"
            editable
          />

          <EditableCardSection
            :name="`${name}.headline`"
            title="Headline"
            icon="tabler-typography"
            iconVariant="success"
            editable
          />

          <EditableCardSection
            :name="`${name}.description`"
            title="Description (optional)"
            icon="tabler-list-details"
            iconVariant="gray"
            editable
            :required="false"
          />

          <EditableCardSection
            :name="`${name}.cta`"
            title="CTA button"
            icon="tabler-urgent"
            iconVariant="error"
            editable
          />
        </div>
      </template>

      <template #right>
        <ImageGenerator
          :name="imageGenerationFieldName"
          @generatePrompts="emit('generatePrompts')"
        >
          <template #title> Generate ad visualization prompts </template>
          <template #description>
            6 ad image prompts will be generated based on ad text copy; please
            verify the accuracy of all the information before proceeding.
          </template>
        </ImageGenerator>
      </template>
    </ModalStandard>
  </SelectableCard>
</template>
