<script setup lang="ts">
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
  UmbrellaCampaignMotiveAndBarrier,
} from "@/services/projects/UmbrellaCampaignsApi";
import { useField } from "vee-validate";

const props = defineProps<{
  name: string;
}>();

const { t } = useI18n();
const submitCount = useSubmitCount();

const { data } = useMultiStepFormContext<UmbrellaCampaignData>();

const brandId = useBrandId();
const projectId = useProjectId();
const umbrellaCampaignId = computed(() => data.value.id);

const { value: motiveAndBarrier, setValue } =
  useField<UmbrellaCampaignMotiveAndBarrier>(() => props.name, undefined);

const type = computed(() =>
  motiveAndBarrier.value.name.endsWith("_motive") ? "motive" : "barrier",
);

const getIcon = (name: string) => {
  const iconMap: Record<string, string> = {
    cultural_motive: "tabler-globe",
    cultural_barrier: "tabler-globe",
    social_motive: "tabler-friends",
    social_barrier: "tabler-friends",
    product_motive: "tabler-shopping-cart",
    product_barrier: "tabler-shopping-cart",
    media_motive: "tabler-news",
    media_barrier: "tabler-news",
  };

  return iconMap[name] || "tabler-globe";
};

const getPlaceholder = (name: string) => {
  const placeholderMap: Record<string, string> = {
    cultural_motive: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.cultural_motive",
    ),
    cultural_barrier: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.cultural_barrier",
    ),
    social_motive: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.social_motive",
    ),
    social_barrier: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.social_barrier",
    ),
    product_motive: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.product_motive",
    ),
    product_barrier: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.product_barrier",
    ),
    media_motive: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.media_motive",
    ),
    media_barrier: t(
      "umbrella-campaign.step-drama.motives-and-barriers.placeholder-motives.media_barrier",
    ),
  };

  return placeholderMap[name] || "";
};

const isCompleted = computed(() => {
  return !!motiveAndBarrier.value?.text;
});

const regenerateResource = async () => {
  const { data: generated } =
    await UmbrellaCampaignsApi.askLucaForOneBuyerPersonMotiveAndBarrier(
      brandId,
      projectId,
      umbrellaCampaignId.value,
      { motive_barrier_selected: motiveAndBarrier.value },
    );

  setValue({
    ...motiveAndBarrier.value,
    ...generated.answer[motiveAndBarrier.value.name],
  });

  return generated;
};
</script>

<template>
  <CardBase
    padding="sm"
    class="min-h-[220px] tw:flex tw:flex-col tw:gap-4 tw:p-4"
    :outlineColor="
      isCompleted ? 'success' : submitCount > 0 ? 'error' : 'default'
    "
  >
    <CardTitle
      :iconVariant="type === 'motive' ? 'success' : 'error'"
      :icon="getIcon(motiveAndBarrier.name)"
    >
      {{
        t(
          `umbrella-campaign.step-drama.motives-and-barriers.${motiveAndBarrier.name}.display_name`,
        )
      }}

      <template #subtitle>
        {{
          t(
            `umbrella-campaign.step-drama.motives-and-barriers.${motiveAndBarrier.name}.description`,
          )
        }}
      </template>
    </CardTitle>

    <div class="tw:flex tw:items-start tw:gap-2">
      <div class="tw:flex tw:grow tw:flex-col">
        <FieldTextarea
          :name="`${props.name}.text`"
          :placeholder="getPlaceholder(motiveAndBarrier.name)"
          type="textarea"
          required
          :rows="2"
          :maxVisibleLines="2"
        />
      </div>
      <ButtonGenerateIdea :fetcher="regenerateResource" square size="sm">
        {{ $t("forms.give-me-ideas.button") }}
      </ButtonGenerateIdea>
    </div>
  </CardBase>
</template>
