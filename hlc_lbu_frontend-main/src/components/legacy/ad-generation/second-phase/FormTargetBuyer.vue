<script lang="ts" setup>
import { array, object } from "yup";
import { TargetBuyer, targetBuyerSchema } from "./cards/BuyerCard.vue";
import { toTypedSchema } from "@vee-validate/yup";
import SecondPhaseBuyerPerson from "@/services/legacy/SecondPhaseBuyerPerson";
import { UnidentifiedError } from "@/services/common-errors";
import SecondPhaseProduct from "@/services/legacy/SecondPhaseProduct";

const store = useAdGenerationStore();

if (!store.data.buyer_persons) {
  throw new UnidentifiedError();
}

// Map the person buyers
const initialValues = store.data.buyer_persons.map<TargetBuyer>((person) => {
  return {
    id: person.Buyer_Persona.id,
    selected: person.Buyer_Persona.preferred === 1,
    title: person.Buyer_Persona.Title,
    name: person.Buyer_Persona.Name,
    age: person.Buyer_Persona.Age,
    description: person.Buyer_Persona.Description,
    lives: person.Buyer_Persona.Details.Lives,
    values: person.Buyer_Persona.Details.Values,
    goals: person.Buyer_Persona.Details.Goals,
    needs: person.Buyer_Persona.Details.Needs,
    painPoints: person.Buyer_Persona.Details.Pain_Points,
    imageGeneration: undefined,
  };
});

// Map the prompts and fetch the image
const initialSelectedBuyer = initialValues.find((buyer) => buyer.selected);
if (initialSelectedBuyer) {
  const selectedPrompt = store.data.buyer_person_image_prompts?.find(
    (prompt) => prompt.preferred,
  );
  const imageBlob = await SecondPhaseBuyerPerson.getImage(
    store.projectId,
    true,
  );

  initialSelectedBuyer.imageGeneration = {
    prompts: store.data.buyer_person_image_prompts?.map(
      (prompt) => prompt.description,
    ),
    selectedPromptIndex: selectedPrompt?.id,
    selectedPrompt: selectedPrompt?.description,
    generatedImage: imageBlob,
  };
}

const { handleSubmit, errors, setFieldValue, values, submitCount } =
  useFormWithErrorScrolling({
    initialValues: {
      targetBuyers: initialValues,
    },
    validationSchema: toTypedSchema(
      object().shape({
        targetBuyers: array()
          .of(targetBuyerSchema)
          .required()
          .test((items) => {
            return items.some((item) => item.selected);
          })
          .test(
            "need-image",
            "You have to generate an image in the selected concept.",
            (items) => {
              const selected = items.find((item) => item.selected);
              return !!selected?.imageGeneration?.generatedImage;
            },
          ),
      }),
    ),
    keepValuesOnUnmount: true,
  });

const selectedBuyer = computed(() =>
  values.targetBuyers?.find((item) => item.selected),
);

const isLoading = ref(false);

const onSubmit = handleSubmit(async (values) => {
  if (
    !selectedBuyer.value ||
    !selectedBuyer.value.imageGeneration?.generatedImage ||
    selectedBuyer.value.imageGeneration?.selectedPromptIndex === undefined
  ) {
    throw new UnidentifiedError();
  }

  isLoading.value = true;

  // Save data locally
  const buyerPersons = values.targetBuyers.map((buyer) =>
    SecondPhaseBuyerPerson.mapSchemaToData(buyer),
  );
  store.data.buyer_persons = buyerPersons;
  store.data.preferred_buyer_person = buyerPersons.find(
    (person) => person.Buyer_Persona.preferred === 1,
  );

  // Save all buyers. We sort the array to move the selected buyer to the end
  const sortedPersons = [...buyerPersons].sort((a, b) =>
    a.Buyer_Persona.preferred > b.Buyer_Persona.preferred ? 1 : -1,
  );
  for (const person of sortedPersons) {
    // Set as preferred first, because the save endpoint doesn't accept an id, it saves the
    // preferred buyer person
    await SecondPhaseBuyerPerson.setPreferred(
      store.projectId,
      person.Buyer_Persona.id,
    );

    // Save the buyer person
    await SecondPhaseBuyerPerson.savePreferred(store.projectId, person);
  }

  // Set the preferred prompt
  const preferredPromptResponse =
    await SecondPhaseBuyerPerson.setPreferredPrompt(
      store.projectId,
      selectedBuyer.value.imageGeneration.selectedPromptIndex,
    );
  // Save data from response
  store.data.selected_buyer_person_image_prompt =
    preferredPromptResponse.data.selected_buyer_person_image_prompt;

  // Upload the image
  if (selectedBuyer.value.imageGeneration.generatedImage instanceof Blob) {
    await SecondPhaseBuyerPerson.uploadImage(
      store.projectId,
      selectedBuyer.value.imageGeneration.generatedImage,
    );
  }

  // Generate products
  const productsResponse = await SecondPhaseProduct.generate(store.projectId);

  // Save data from response
  store.data.products = productsResponse.data.products;
  store.data.preferred_product = undefined;

  // Go to next step
  store.goNext();
});

const handleChecked = (checked: boolean, value: TargetBuyer) => {
  const index = values.targetBuyers?.findIndex(
    (buyer) => buyer.id === value.id,
  );

  if (checked) {
    // Uncheck all except this one
    values.targetBuyers?.forEach((_, _index) => {
      if (index != _index) {
        setFieldValue(`targetBuyers.${_index}.selected`, false);
      }
    });
  }
};

const areCardsExpanded = ref(false);

// Keep the height of cards
useMaxHeightCards(
  [
    ".card-header",
    ".card-title-and-paragraph",
    ".card-lives",
    ".card-values",
    ".card-goals",
    ".card-needs",
    ".card-pain-points",
  ],
  [values, areCardsExpanded],
);
</script>

<template>
  <form
    @submit="onSubmit"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        {{ $t("process.target-buyer.title") }}
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        {{ $t("process.target-buyer.description") }}
      </WizardCardParagraph>
    </div>

    <CardGrid>
      <BuyerCard
        v-for="(_buyer, index) in values.targetBuyers"
        :name="`targetBuyers[${index}]`"
        :projectId="store.projectId"
        @checked="handleChecked"
        v-model:expanded="areCardsExpanded"
        class="tw:grow tw:basis-0"
      />
    </CardGrid>

    <Alert v-if="errors.targetBuyers && submitCount > 0" type="error">
      {{ errors.targetBuyers }}
    </Alert>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :disabled="!selectedBuyer" :isLoading="isLoading" />
    </WizardCardActions>
  </form>
</template>
