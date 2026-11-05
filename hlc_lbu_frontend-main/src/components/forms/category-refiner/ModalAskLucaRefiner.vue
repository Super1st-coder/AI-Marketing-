<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { RefinerItem } from "./categoryRefinerTypes";

export type AskLucaFetcher = (
  category: string,
  description: string,
  question: string,
) => Promise<RefinerAttributes>;

export interface ModalAskLucaRefinerProps {
  name: string;
  title?: string;
  description?: string;
  question?: string;
  questionPlaceholder?: string;
  fetcher: AskLucaFetcher;
}

const props = defineProps<ModalAskLucaRefinerProps>();
const emit = defineEmits<{
  save: [attributes: string[]];
}>();

const { t } = useI18n();

const isOpen = defineModel<boolean>({ required: true });

const { handleSubmit } = useFormWithErrorScrolling({
  validationSchema: toTypedSchema(
    object({
      description: string().required(),
    }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);
const generatedItems = ref<RefinerItem[]>();

const titleText = computed(
  () =>
    props.title ??
    t(`category-refiner.ask-luca.categories.${props.name}.title`),
);

const descriptionText = computed(
  () =>
    props.description ??
    t(`category-refiner.ask-luca.categories.${props.name}.description`),
);

const questionText = computed(
  () =>
    props.question ??
    t(`category-refiner.ask-luca.categories.${props.name}.question`),
);

const questionPlaceholderText = computed(
  () =>
    props.questionPlaceholder ??
    t(`category-refiner.ask-luca.categories.${props.name}.questionPlaceholder`),
);

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  const response = await props.fetcher(
    props.name,
    values.description,
    questionText.value,
  );
  generatedItems.value = Object.keys(response)
    .map((key) => response[key])
    .flat()
    .map((attribute) => ({ name: attribute, checked: false }));

  isLoading.value = false;
});

// Save but show alert first
const alertMessage = ref<string>();
const handleSave = useDoubleClickWithMessage(
  () => {
    if (generatedItems.value) {
      const names = generatedItems.value
        .filter((item) => item.checked)
        .map((item) => item.name);
      emit("save", names);
    }

    isOpen.value = false;
    generatedItems.value = undefined;
  },
  alertMessage,
  () => t("category-refiner.ask-luca.save-warning"),
);

// Go back but show alert first
const handleGoBack = useDoubleClickWithMessage(
  () => {
    generatedItems.value = undefined;
  },
  alertMessage,
  () => t("category-refiner.ask-luca.go-back-warning"),
);

// Clear alert if the items change
watch(
  generatedItems,
  () => {
    alertMessage.value = undefined;
  },
  { deep: true },
);

// Clear alert when the modal is closed
watch(isOpen, (isOpen) => {
  if (!isOpen) {
    alertMessage.value = undefined;
  }
});
</script>

<template>
  <Modal
    v-model="isOpen"
    innerClass="tw:max-w-[980px] tw:py-6 tw:px-10"
    closeButton
  >
    <PageTitle is="h2" class="tw:mb-6">
      {{ titleText }}
      <template #description>
        {{ descriptionText }}
      </template>
    </PageTitle>

    <form class="tw:flex tw:w-full tw:flex-col" @submit.prevent="onSubmit">
      <div class="tw:md:mb-14">
        <template v-if="generatedItems">
          <CardGrid>
            <ModalAskLucaRefinerItem
              v-for="(item, index) in generatedItems"
              :index="index"
              :item="item"
              v-model:items="generatedItems"
            />
          </CardGrid>
        </template>
        <template v-else>
          <FieldTextarea
            name="description"
            :label="questionText"
            :placeholder="questionPlaceholderText"
            :speechRecognition="true"
            required
          />
        </template>

        <Alert v-if="alertMessage" type="error">
          {{ alertMessage }}
        </Alert>
      </div>

      <template v-if="generatedItems">
        <div
          class="tw:flex tw:flex-col tw:justify-between tw:gap-4 tw:py-6 tw:md:flex-row tw:md:gap-8"
        >
          <Button @click="handleSave" class="tw:md:basis-[300px]" type="button">
            {{ $t("global.save") }}
          </Button>

          <Button
            leftIcon="tabler-arrow-left"
            variant="outlined"
            @click="handleGoBack"
            class="tw:md:order-first tw:md:basis-[300px]"
            type="button"
          >
            {{ t("category-refiner.ask-luca.update-response") }}
          </Button>
        </div>
      </template>
      <template v-else>
        <div class="tw:flex tw:justify-end tw:py-6">
          <ButtonNext type="submit" :isLoading="isLoading" />
        </div>
      </template>
    </form>
  </Modal>
</template>
