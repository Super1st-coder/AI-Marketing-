<script lang="ts" setup>
import CampaignsApi, {
  CampaingStyleData,
} from "@/services/projects/CampaignsApi";
import { LlmOutputError } from "@/services/common-errors";

const props = defineProps<{
  setStyle: (selectedCampaign: CampaingStyleData) => Promise<void>;
  helpVideoUrl?: string;
}>();

const emit = defineEmits<{
  goNext: [];
}>();

const { t } = useI18n();
const styles = (await CampaignsApi.getListCampaignStyleData()).data;

const generalErrorMessage = ref<string>();
const selectedCard = ref<CampaingStyleData | undefined>();

const handleCampaignSelect = async (selectedCampaign: CampaingStyleData) => {
  selectedCard.value = selectedCampaign;

  try {
    generalErrorMessage.value = undefined;

    await props.setStyle(selectedCampaign);

    emit("goNext");
  } catch (error) {
    if (error instanceof LlmOutputError) {
      generalErrorMessage.value = t(`errors.${error.message}.title`);
      selectedCard.value = undefined;
    } else {
      throw error;
    }
  }
};
</script>

<template>
  <div class="tw:grid tw:grid-cols-1 tw:gap-6">
    <!-- TODO: add help video URL later -->
    <PageTitle :helpButton="!!helpVideoUrl" :helpVideoUrl="helpVideoUrl">
      <slot name="title">
        {{ $t("image-generation.style-selection.title") }}
      </slot>

      <template v-if="$slots.description" #description>
        <slot name="description">
          {{ $t("image-generation.style-selection.description") }}
        </slot>
      </template>
    </PageTitle>

    <CardGrid>
      <StyleCard
        v-for="(campaign, index) in styles"
        :selectedCard="selectedCard"
        :key="index"
        :style="campaign"
        @select="handleCampaignSelect"
      />
    </CardGrid>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>
  </div>
</template>
