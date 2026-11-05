<script lang="ts" setup>
const store = useAdGenerationStore();

const hypothesis = store.data.hypothesis_builder_preferred_option;
const hypothesisParagraph = `IF we offer ${hypothesis?.Hypothesis_option.Goal} to ${hypothesis?.Hypothesis_option.Audience}, THEN we will ${hypothesis?.Hypothesis_option.Testing_Variable}`;

const creativeConceptParagraph =
  store.data.preferred_campaign?.sections.concept.description;

const targetBuyerParagraph =
  store.data.preferred_buyer_person?.Buyer_Persona.Description;

const productParagraph =
  store.data.preferred_product?.Product.Details.Description;
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]">
    <div>
      <WizardCardTitle>
        Welcome to your Marketing Funnel Builder
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Launch fully tailored marketing campaigns to capture your audience’s
        attention.
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-8">
      <Separator />

      <div class="tw:grid tw:gap-8 tw:lg:grid-cols-2 tw:lg:gap-16">
        <div>
          <CardTitle iconVariant="info" iconSrc="/images/documents.png">
            Hypothesis
          </CardTitle>

          <CardParagraph>
            {{ hypothesisParagraph }}
          </CardParagraph>
        </div>

        <div>
          <CardTitle iconVariant="error" iconSrc="/images/magic-ball.png">
            Creative Concept:
          </CardTitle>

          <CardParagraph>
            {{ creativeConceptParagraph }}
          </CardParagraph>
        </div>
      </div>

      <Separator />

      <div class="tw:flex tw:flex-col tw:gap-8 tw:lg:gap-16">
        <div>
          <CardTitle iconVariant="primary" iconSrc="/images/dart.png">
            Target Buyer:
          </CardTitle>

          <CardParagraph>
            {{ targetBuyerParagraph }}
          </CardParagraph>
        </div>

        <div>
          <CardTitle iconVariant="error" iconSrc="/images/diamond.png">
            Product:
          </CardTitle>

          <CardParagraph>
            {{ productParagraph }}
          </CardParagraph>
        </div>

        <!-- <div>
          <CardTitle iconVariant="success" iconSrc="/images/speaker.png">
            Brand Voice %
          </CardTitle>

          <CardParagraph>
            Lorem ipsum, dolor sit amet consectetur adipisicing elit. Laborum
            ipsa, dolorum ex recusandae eius quidem, similique, accusamus ipsam
            alias rem aliquam provident expedita assumenda nemo quo delectus
            magnam amet. Incidunt.
          </CardParagraph>
        </div> -->
      </div>

      <Separator />
    </div>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext @click="store.goNext" />
    </WizardCardActions>
  </div>
</template>
