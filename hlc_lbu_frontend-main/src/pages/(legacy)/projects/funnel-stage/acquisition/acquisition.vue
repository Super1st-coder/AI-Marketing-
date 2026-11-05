<script lang="ts" setup>
import { object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRouter } from "vue-router";

const funnelBuilderStore = useFunnelBuilderStore();
const router = useRouter();

const { handleSubmit, errors, submitCount } = useFormWithErrorScrolling({
  initialValues: {
    funnelStageType: funnelBuilderStore.data.funnelStageType,
  },
  validationSchema: toTypedSchema(
    object().shape({
      funnelStageType: string().required("You need to select one type."),
    }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data in state
  funnelBuilderStore.data.funnelStageType = values.funnelStageType;

  // Go to next screen
  router.push({ name: "PaidSocial" });
});
//#endregion
</script>

<template>
  <WizardCard paddingY="lg">
    <form
      @submit="onSubmit"
      class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
    >
      <div>
        <WizardCardTitle>
          Select type of the acquisition funnel
          <template #button>
            <HelpButton> Help info </HelpButton>
          </template>
        </WizardCardTitle>

        <WizardCardParagraph>
          Choose the funnel that best fits your current goals — whether it’s
          quick wins, long-term growth, or unique opportunities.
        </WizardCardParagraph>
      </div>

      <div class="tw:flex tw:flex-col tw:gap-8">
        <Separator />

        <div>
          <CardTitle> Paid </CardTitle>

          <CardParagraph>
            Fast results with immediate impact, but often costly and
            unsustainable in the long run. Best for quick wins and short-term
            campaigns.
          </CardParagraph>
        </div>

        <CardGrid>
          <FunnelTypeCard
            name="funnelStageType"
            value="paid-search-high-intent"
            class="tw:grow tw:basis-0"
          >
            <template #title> Paid Search (High Intent) </template>

            <template #description>
              Targets users actively searching for specific solutions with
              strong purchase intent via search ads for high-conversion
              keywords.
            </template>
          </FunnelTypeCard>

          <FunnelTypeCard
            name="funnelStageType"
            value="paid-search-low-intent"
            class="tw:grow tw:basis-0"
          >
            <template #title> Paid Search (Low Intent) </template>

            <template #description>
              Reaches users researching broader, informational topics through
              search ads, aiming to nurture them towards a future purchase.
              keywords.
            </template>
          </FunnelTypeCard>

          <FunnelTypeCard
            name="funnelStageType"
            value="paid-social"
            class="tw:grow tw:basis-0"
          >
            <template #title>Paid Social</template>

            <template #description>
              Uses paid social media ads to target specific audiences based on
              demographics and interests to drive awareness, engagement, or
              conversions.
            </template>
          </FunnelTypeCard>
        </CardGrid>

        <Separator />

        <div>
          <CardTitle> Organic </CardTitle>

          <CardParagraph>
            Steady and reliable results over time, focused on building
            sustainable growth through consistent efforts without ongoing costs.
          </CardParagraph>
        </div>

        <CardGrid>
          <FunnelTypeCard
            name="funnelStageType"
            value="organic-search-low-intent"
            class="tw:grow tw:basis-0"
          >
            <template #title> Organic Search (Low Intent) </template>

            <template #description>
              Engages users with SEO-optimized content focused on educating and
              nurturing users in the early stages of their research.
            </template>
          </FunnelTypeCard>

          <FunnelTypeCard
            name="funnelStageType"
            value="organic-search-high-intent"
            class="tw:grow tw:basis-0"
          >
            <template #title> Organic Search (High Intent) </template>

            <template #description>
              Attracts users through SEO for high-intent keywords, focusing on
              converting visitors who are ready to make a purchase.
            </template>
          </FunnelTypeCard>

          <FunnelTypeCard
            name="funnelStageType"
            value="organic-social"
            class="tw:grow tw:basis-0"
          >
            <template #title>Organic Social</template>

            <template #description>
              Builds brand awareness and engagement through regular, non-paid
              social media posts to grow and nurture an organic following.
            </template>
          </FunnelTypeCard>
        </CardGrid>

        <Separator />

        <div>
          <CardTitle> Other </CardTitle>

          <CardParagraph>
            Unpredictable results, but with high potential for growth and unique
            opportunities. Ideal for building strong, long-term relationships
            and brand advocacy.
          </CardParagraph>
        </div>

        <CardGrid>
          <FunnelTypeCard
            name="funnelStageType"
            value="community-groups"
            class="tw:grow tw:basis-0"
          >
            <template #title> Free - Community Groups </template>

            <template #description>
              Engages with potential users through active participation in
              relevant community groups like Slack or Discord to generate
              organic leads.
            </template>
          </FunnelTypeCard>

          <FunnelTypeCard
            name="funnelStageType"
            value="cold-email"
            class="tw:grow tw:basis-0"
          >
            <template #title> Cold Email </template>

            <template #description>
              Initiates direct outreach to targeted prospects via personalized
              emails, aiming to generate interest and conversions from a cold
              audience.
            </template>
          </FunnelTypeCard>

          <FunnelTypeCard
            name="funnelStageType"
            value="influencer-marketing"
            class="tw:grow tw:basis-0"
          >
            <template #title>Influencer Marketing</template>

            <template #description>
              Leverages influencers to promote your product to their engaged
              audience, driving traffic and conversions through trusted
              recommendations.
            </template>
          </FunnelTypeCard>
        </CardGrid>
      </div>

      <Alert v-if="errors.funnelStageType && submitCount > 0" type="error">
        {{ errors.funnelStageType }}
      </Alert>

      <WizardCardActions>
        <WizardButtonGoBack @click="router.push({ name: 'FunnelStage' })" />

        <WizardButtonNext :isLoading="isLoading" />
      </WizardCardActions>
    </form>
  </WizardCard>
</template>
