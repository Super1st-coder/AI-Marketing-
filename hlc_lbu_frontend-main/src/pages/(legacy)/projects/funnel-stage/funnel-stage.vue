<script lang="ts" setup>
import { object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRouter } from "vue-router";

const funnelBuilderStore = useFunnelBuilderStore();
const router = useRouter();

const { handleSubmit, errors, submitCount } = useFormWithErrorScrolling({
  initialValues: {
    funnelStage: funnelBuilderStore.data.funnelStage,
  },
  validationSchema: toTypedSchema(
    object().shape({
      funnelStage: string().required("You need to select one stage."),
    }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data in state
  funnelBuilderStore.data.funnelStage = values.funnelStage;
  funnelBuilderStore.data.funnelStageType = undefined;

  // Go to next screen
  router.push({ name: "FunnelStageAcquisition" });
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
          Choose your funnel stage
          <template #button>
            <HelpButton> Help info </HelpButton>
          </template>
        </WizardCardTitle>

        <WizardCardParagraph>
          Select the funnel stage to create a targeted marketing campaign, from
          awareness to retention, based on your strategy.
        </WizardCardParagraph>
      </div>

      <CardGrid>
        <FunnelStageCard name="funnelStage" value="awareness">
          <template #title> Awareness </template>

          <template #description>
            Attract potential users by making your product discoverable through
            targeted marketing channels.
          </template>
        </FunnelStageCard>

        <FunnelStageCard name="funnelStage" value="acquisition">
          <template #title> Acquisition </template>

          <template #description>
            Convert visitors into leads by capturing their interest through
            sign-ups or initial actions.
          </template>
        </FunnelStageCard>

        <FunnelStageCard name="funnelStage" value="activation">
          <template #title> Activation </template>

          <template #description>
            Engage users by delivering value early on, helping them experience
            the core benefit of your product.
          </template>
        </FunnelStageCard>

        <FunnelStageCard name="funnelStage" value="retention">
          <template #title> Retention </template>

          <template #description>
            Keep users coming back by maintaining engagement and providing
            continued value over time.
          </template>
        </FunnelStageCard>

        <FunnelStageCard name="funnelStage" value="revenue">
          <template #title> Revenue </template>

          <template #description>
            Monetize users by turning them into paying customers through
            relevant product or service offers.
          </template>
        </FunnelStageCard>

        <FunnelStageCard name="funnelStage" value="referral">
          <template #title> Referral </template>

          <template #description>
            Encourage satisfied users to refer others, driving organic growth
            and increasing your user base.
          </template>
        </FunnelStageCard>
      </CardGrid>

      <Alert v-if="errors.funnelStage && submitCount > 0" type="error">
        {{ errors.funnelStage }}
      </Alert>

      <WizardCardActions>
        <WizardButtonGoBack
          @click="router.push({ name: 'AdGenerationProcess' })"
        />

        <WizardButtonNext :isLoading="isLoading" />
      </WizardCardActions>
    </form>
  </WizardCard>
</template>
