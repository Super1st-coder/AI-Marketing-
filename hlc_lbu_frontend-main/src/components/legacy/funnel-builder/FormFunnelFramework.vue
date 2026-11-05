<script lang="ts" setup>
import { object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRouter } from "vue-router";

const store = useAdGenerationStore();
const funnelBuilderStore = useFunnelBuilderStore();
const router = useRouter();

const { handleSubmit, errors, submitCount } = useFormWithErrorScrolling({
  initialValues: {
    funnelFramework: funnelBuilderStore.data.funnelFramework,
  },
  validationSchema: toTypedSchema(
    object().shape({
      funnelFramework: string().required("You need to select one framework."),
    }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data in state
  funnelBuilderStore.data.funnelFramework = values.funnelFramework;
  funnelBuilderStore.data.funnelStage = undefined;
  funnelBuilderStore.data.funnelStageType = undefined;

  // Go to next screen
  router.push({ name: "FunnelStage" });
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
        Choose your funnel framework
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Select the marketing funnel framework that best fits your growth
        strategy and customer journey.
      </WizardCardParagraph>
    </div>

    <CardGrid>
      <FunnelFrameWorkCard
        name="funnelFramework"
        value="aaarrr"
        class="tw:grow tw:basis-0"
      >
        <template #title> AAARRR </template>

        <template #description>
          Focuses on the stages of the customer journey: Awareness, Acquisition,
          Activation, Retention, Revenue, and Referral. This framework is
          designed to help optimize each step to drive growth and retention.
        </template>
      </FunnelFrameWorkCard>

      <FunnelFrameWorkCard
        name="funnelFramework"
        value="race"
        class="tw:grow tw:basis-0"
      >
        <template #title> RACE </template>

        <template #description>
          A digital marketing planning framework for driving growth through
          customer interaction and engagement. It focuses on four stages: Reach
          (awareness), Act (engagement), Convert (purchase), and Engage
          (long-term retention).
        </template>
      </FunnelFrameWorkCard>

      <FunnelFrameWorkCard
        name="funnelFramework"
        value="aida"
        class="tw:grow tw:basis-0"
      >
        <template #title> AIDA </template>

        <template #description>
          A classic framework for structuring marketing communications. It
          focuses on capturing the user's attention, generating interest,
          building desire, and prompting action (conversion).
        </template>
      </FunnelFrameWorkCard>
    </CardGrid>

    <Alert v-if="errors.funnelFramework && submitCount > 0" type="error">
      {{ errors.funnelFramework }}
    </Alert>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :isLoading="isLoading" />
    </WizardCardActions>
  </form>
</template>
