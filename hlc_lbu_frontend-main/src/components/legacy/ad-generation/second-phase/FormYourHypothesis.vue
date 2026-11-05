<script lang="ts" setup>
import { array, object } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import {
  YourHypothesis,
  yourHypothesisSchema,
} from "./cards/YourHypothesisCard.vue";
import SecondPhaseHypothesis, {
  HypothesisBuilderOptionData,
  processHypothesis,
} from "@/services/legacy/SecondPhaseHypothesis";
import { UnidentifiedError } from "@/services/common-errors";

const { t } = useI18n();

const store = useAdGenerationStore();
const projectId = store.projectId;

const sentence = t("process.your-hypothesis.card.sentence", {
  offer: "{offer}",
  to: "{to}",
  then: "{then}",
});

const elementsResponse =
  await SecondPhaseHypothesis.getBuilderElements(projectId);
const processedElements = processHypothesis(elementsResponse);

const items = {
  offer: processedElements.hypothesis_elements,
  to: [processedElements.buyer_person],
  then: processedElements.goals,
};

const options = [items, items, items];

const initialHypothesis: YourHypothesis[] = options.map((option, index) => {
  const originalOption = store.data.hypothesis_builder_options?.[index];

  return {
    id: index,
    selected: originalOption?.Hypothesis_option?.preferred === 1,
    name: t("process.your-hypothesis.card.title", {
      index: index + 1,
    }),
    options: {
      offer:
        originalOption?.Hypothesis_option.Goal ??
        option.offer[index % option.offer.length],
      to:
        originalOption?.Hypothesis_option.Audience ??
        option.to[index % option.to.length],
      then:
        originalOption?.Hypothesis_option.Testing_Variable ??
        option.then[index % option.then.length],
    },
  };
});

const { handleSubmit, values, setFieldValue } = useFormWithErrorScrolling({
  initialValues: {
    yourHypothesis: initialHypothesis,
  },
  validationSchema: toTypedSchema(
    object().shape({
      yourHypothesis: array()
        .of(yourHypothesisSchema)
        .required()
        .test((items) => {
          return items.some((item) => item.selected);
        }),
    }),
  ),
  keepValuesOnUnmount: true,
});

const selectedHypothesis = computed(() =>
  values.yourHypothesis?.find((item) => item.selected),
);

const handleChecked = (checked: boolean, value: YourHypothesis) => {
  const index = values.yourHypothesis?.findIndex(
    (buyer) => buyer.name === value.name,
  );

  if (checked) {
    // Uncheck all except this one
    values.yourHypothesis?.forEach((_, _index) => {
      if (index != _index) {
        setFieldValue(`yourHypothesis.${_index}.selected`, false);
      }
    });
  }
};

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  if (!selectedHypothesis.value) {
    throw new UnidentifiedError();
  }

  isLoading.value = true;

  // Send data
  const hypothesisOptions =
    values.yourHypothesis.map<HypothesisBuilderOptionData>((hypothesis) => ({
      Hypothesis_option: {
        id: hypothesis.id,
        Goal: hypothesis.options?.offer,
        Audience: hypothesis.options?.to,
        preferred: hypothesis.selected ? 1 : 0,
        Testing_Variable: hypothesis.options?.then,
      },
    }));
  const saveResponse = await SecondPhaseHypothesis.saveOptionList(
    projectId,
    hypothesisOptions,
  );

  // Save data from response
  store.data.hypothesis_builder_options =
    saveResponse.data.hypothesis_builder_options;
  store.data.hypothesis_builder_preferred_option =
    saveResponse.data.hypothesis_builder_options.find(
      (option) => option.Hypothesis_option.preferred === 1,
    );

  // Set preferred
  await SecondPhaseHypothesis.setPreferred(
    projectId,
    selectedHypothesis.value.id,
  );

  // Go to the next screen
  store.goNext();
});
</script>

<template>
  <form
    @submit="onSubmit"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        {{ $t("process.your-hypothesis.title") }}
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        {{ $t("process.your-hypothesis.description") }}
      </WizardCardParagraph>
    </div>

    <CardGrid>
      <YourHypothesisCard
        v-for="(item, index) in values.yourHypothesis"
        :name="`yourHypothesis[${index}]`"
        @checked="(checked) => handleChecked(checked, item)"
        :sentence="sentence"
        :options="options[index]"
        class="tw:grow tw:basis-0"
      />
    </CardGrid>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext
        :disabled="!selectedHypothesis"
        :isLoading="isLoading"
      />
    </WizardCardActions>
  </form>
</template>
