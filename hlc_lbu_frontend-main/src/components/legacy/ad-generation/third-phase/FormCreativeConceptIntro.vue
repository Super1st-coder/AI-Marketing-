<script lang="ts" setup>
const store = useAdGenerationStore();

const hypothesis = store.data.hypothesis_builder_preferred_option;
const hypothesisParagraph = `IF we offer ${hypothesis?.Hypothesis_option.Goal} to ${hypothesis?.Hypothesis_option.Audience}, THEN we will ${hypothesis?.Hypothesis_option.Testing_Variable}`;

const productParagraph =
  store.data.preferred_product?.Product.Details.Description;

const targetBuyerParagraph =
  store.data.preferred_buyer_person?.Buyer_Persona.Description;

const audienceParagraph = store.data.preferred_audience?.Audience;
//#endregion
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]">
    <div>
      <WizardCardTitle>
        Welcome to your creative concept engine
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Here's a quick reminder of what we’re working with.
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-8">
      <Separator />

      <div>
        <CardTitle iconVariant="info" iconSrc="/images/documents.png">
          Hypothesis
        </CardTitle>

        <CardParagraph>
          {{ hypothesisParagraph }}
        </CardParagraph>
      </div>

      <Separator />

      <div class="tw:grid tw:gap-8 tw:lg:grid-cols-3 tw:lg:gap-16">
        <div>
          <CardTitle iconVariant="error" iconSrc="/images/diamond.png">
            Product
          </CardTitle>

          <CardParagraph>
            {{ productParagraph }}
          </CardParagraph>
        </div>

        <div>
          <CardTitle iconVariant="error" iconSrc="/images/dart.png">
            Buyer
          </CardTitle>

          <CardParagraph>
            {{ targetBuyerParagraph }}
          </CardParagraph>
        </div>

        <div>
          <CardTitle iconVariant="success" iconSrc="/images/family.png">
            Audience
          </CardTitle>

          <CardParagraph>
            {{ audienceParagraph }}
          </CardParagraph>
        </div>
      </div>

      <Separator />
    </div>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext @click="store.goNext" />
    </WizardCardActions>
  </div>
</template>
