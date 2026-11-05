<script setup lang="ts">
import CampaignsApi from "@/services/projects/CampaignsApi";
import { FunnelPaidSocialFormData } from "../FunnelPaidSocialForm.vue";
import AdStructureApi, {
  FunnelFlowNotFoundError,
} from "@/services/funnel-flow/paid-social/AdStructureApi";

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();

const { data } = await CampaignsApi.getOne(brandId, projectId, campaignId);

const { goNext, goBack } = useMultiStepFormContext<FunnelPaidSocialFormData>();

let hasFunnelFlow = ref(false);

try {
  // Try to get the funnel flow
  const adStructure = await AdStructureApi.getAdStructureByChannelGroup(
    brandId,
    campaignId,
    2,
  );
  hasFunnelFlow.value = adStructure.data.ad_sets.length > 0;
} catch (error) {
  // If the funnel flow is not found, set hasFunnelFlow to false
  if (error instanceof FunnelFlowNotFoundError) {
    hasFunnelFlow.value = false;
  } else {
    throw error;
  }
}

const isCreateModalOpen = ref(false);

const handleCreateNewStructure = () => {
  if (hasFunnelFlow.value) {
    goNext();
  } else {
    isCreateModalOpen.value = true;
  }
};
</script>

<template>
  <FormStepLayout as="div">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=js4olusGJ1I"
    >
      {{ $t("funnel-flow.paid-social.structure.title") }}
    </PageTitle>

    <div class="tw:grid tw:gap-[18px] tw:lg:grid-cols-3">
      <FunnelFlowHomeCard icon="tabler:plus">
        <template #title>{{
          $t("funnel-flow.paid-social.structure.cards.start-from-scratch.title")
        }}</template>

        <template #description>
          {{
            $t(
              "funnel-flow.paid-social.structure.cards.start-from-scratch.description",
            )
          }}
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="handleCreateNewStructure"
          >
            {{
              $t(
                "funnel-flow.paid-social.structure.cards.start-from-scratch.action",
              )
            }}
          </Button>
        </template>
      </FunnelFlowHomeCard>

      <!-- <FunnelFlowHomeCard icon="tabler:template">
        <template #title>Use a Template</template>

        <template #description>
          Pick from recommended campaign structures based on common goals and
          best practices.
        </template>

        <template #action>
          <Button size="md" class="tw:w-full" disabled> Use a Template </Button>
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:bookmark">
        <template #title>Load a Saved Structure</template>

        <template #description>
          Reuse a structure from a previous campaign to save time and maintain
          consistency.
        </template>

        <template #action>
          <Button size="md" class="tw:w-full" disabled>
            Load a saved structure
          </Button>
        </template>
      </FunnelFlowHomeCard> -->
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext v-if="hasFunnelFlow" @click="goNext()" />
      </WizardCardActions>
    </template>

    <FunnelPaidSocialFormStructureCreateModal
      v-if="isCreateModalOpen"
      v-model="isCreateModalOpen"
      :campaignName="data.name"
    />
  </FormStepLayout>
</template>
