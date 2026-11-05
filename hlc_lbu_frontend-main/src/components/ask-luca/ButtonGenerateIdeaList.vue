<script setup lang="ts">
interface Props {
  fetcher: (text: string) => Promise<string[]>;
}

const props = defineProps<Props>();

const model = defineModel<string | undefined>({ required: true });
const generated = ref<string[]>([]);
const selected = ref<number | undefined>();
const isLoading = ref(false);
const activeSelectedAnswer = ref<string | undefined>();
const displayRequiredMessage = ref(false);

const handleClick = async () => {
  const currentText = model.value?.trim();

  if (currentText) {
    displayRequiredMessage.value = false;
    isLoading.value = true;

    const generations = await props.fetcher(currentText);
    generated.value = [...generated.value, ...generations];
    isLoading.value = false;
  } else {
    displayRequiredMessage.value = true;
  }
};

const handleSelect = (index: number, newAnswer: string) => {
  selected.value = index;
  const currentFullText = model.value || "";
  let baseText = currentFullText.trim();

  if (activeSelectedAnswer.value) {
    const expectedSuffix = `\n\n${activeSelectedAnswer.value}`;
    if (currentFullText.endsWith(expectedSuffix)) {
      baseText = currentFullText
        .substring(0, currentFullText.length - expectedSuffix.length)
        .trim();
    } else if (currentFullText === activeSelectedAnswer.value) {
      baseText = "";
    }
  }
  if (baseText) {
    model.value = `${baseText}\n\n${newAnswer}`;
  } else {
    model.value = newAnswer;
  }
  activeSelectedAnswer.value = newAnswer;
};
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-4">
    <div
      v-if="generated.length > 0"
      class="tw:grid tw:gap-6 tw:lg:grid-cols-2 tw:xl:grid-cols-3"
    >
      <CardBase
        v-for="(answer, index) in generated"
        class="tw:cursor-pointer tw:p-4 tw:whitespace-pre-line tw:transition tw:active:scale-[102%]"
        :color="selected === index ? 'primary' : 'default'"
        hoverColor="primary"
        @click="handleSelect(index, answer)"
      >
        {{ answer }}
      </CardBase>
    </div>

    <Alert v-if="displayRequiredMessage" type="error" autoScroll>
      {{ $t("forms.give-me-ideas.text-above-error") }}
    </Alert>

    <Button
      leftIcon="custom:hi-luca"
      @click="handleClick"
      :isLoading="isLoading"
      type="button"
      class="tw:self-start"
    >
      <slot>
        {{ $t("forms.give-me-ideas.button") }}
      </slot>
    </Button>
  </div>
</template>
