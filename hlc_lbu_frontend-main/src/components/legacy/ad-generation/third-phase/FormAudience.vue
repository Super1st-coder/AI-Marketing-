<script lang="ts" setup>
import { array, object } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { Audience, audienceSchema } from "./cards/AudienceCard.vue";
import ThirdPhaseAudience, {
  AudienceData,
} from "@/services/legacy/ThirdPhaseAudience";
import { UnidentifiedError } from "@/services/common-errors";

const store = useAdGenerationStore();
const projectId = store.projectId;

if (!store.data.audience) {
  throw new UnidentifiedError();
}

const initialAudiences = store.data.audience.map<Audience>((data) => ({
  id: data.id,
  selected: data.preferred === 1,
  title:
    data.id === 0 ? "HYPER SEGMENTED" : data.id === 1 ? "SEGMENTED" : "BROAD",
  audience: data.Audience,
  age: data.Demographics.Age,
  gender: data.Demographics.Gender,
  location: data.Demographics.Location.join(", "),
  incomeLevel: data.Demographics.IncomeLevel,
  interests: data.Interests,
}));

const { handleSubmit, setFieldValue, values, meta } = useFormWithErrorScrolling(
  {
    initialValues: {
      audiences: initialAudiences,
    },
    validationSchema: toTypedSchema(
      object().shape({
        audiences: array()
          .of(audienceSchema)
          .required()
          .test((items) => {
            return items.some((item) => item.selected);
          }),
      }),
    ),
    keepValuesOnUnmount: true,
  },
);

const handleChecked = (checked: boolean, value: Audience) => {
  const index = values.audiences?.findIndex(
    (item) => item.title === value.title,
  );

  if (checked) {
    // Uncheck all except this one
    values.audiences?.forEach((_, _index) => {
      if (index != _index) {
        setFieldValue(`audiences.${_index}.selected`, false);
      }
    });
  }
};

const areCardsExpanded = ref(false);

// Keep the height of cards
useMaxHeightCards(
  [
    ".card-header",
    ".card-audience",
    ".card-age",
    ".card-gender",
    ".card-location",
    ".card-income-level",
    ".card-interests",
  ],
  [values, areCardsExpanded],
);

//#region Submit

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  const audiences = values.audiences.map<AudienceData>((audience) => {
    const audienceSegment = audience.title.toLowerCase();

    const locations = audience.location
      .split(",")
      .map((location) => location.trim());

    return {
      id: audience.id,
      Audience: audience.audience,
      Interests: audience.interests,
      preferred: audience.selected ? 1 : 0,
      Demographics: {
        Age: audience.age,
        Gender: audience.gender,
        Location: locations,
        IncomeLevel: audience.incomeLevel,
      },
      AudienceSegment: audienceSegment,
    };
  });
  store.data.audience = audiences;
  store.data.preferred_audience = audiences.find(
    (audience) => audience.preferred === 1,
  );

  // Save all audiences. We sort the array to move the selected audience to the end
  const sortedAudiences = [...audiences].sort((a, b) =>
    a.preferred > b.preferred ? 1 : -1,
  );
  for (const audience of sortedAudiences) {
    // Set as preferred first, because the save endpoint doesn't accept an id, it saves the
    // preferred audience
    await ThirdPhaseAudience.setPreferred(projectId, audience.id);

    // Save the audience
    await ThirdPhaseAudience.savePreferred(projectId, audience);
  }

  store.goNext();
});

//#endregion
</script>

<template>
  <form
    @submit="onSubmit"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        Select the audience you’d like to test the hipothesis for
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        It’s an experiment, and it’s your choice. Select 1 audience you’d like
        to test
      </WizardCardParagraph>
    </div>

    <CardGrid>
      <AudienceCard
        v-for="(item, index) in values.audiences"
        :name="`audiences[${index}]`"
        @checked="(checked) => handleChecked(checked, item)"
        v-model:expanded="areCardsExpanded"
        class="tw:grow tw:basis-0"
      />
    </CardGrid>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :isLoading="isLoading" :disabled="!meta.valid" />
    </WizardCardActions>
  </form>
</template>
