<script setup lang="ts">
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
  UmbrellaCampaignResource,
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

const { value: resource, setValue: setResourceValue } =
  useField<UmbrellaCampaignResource>(() => props.name, undefined);

const availabilityOptions = computed(() => [
  {
    value: "SCARCE",
    label: t("umbrella-campaign.step-benefit.resources.label-scarce"),
    color: "error" as const,
    icon: "tabler-mood-sad",
  },
  {
    value: "NEUTRAL",
    label: t("umbrella-campaign.step-benefit.resources.label-neutral"),
    color: "secondary" as const,
    icon: "tabler-mood-empty",
  },
  {
    value: "ABUNDANT",
    label: t("umbrella-campaign.step-benefit.resources.label-abundant"),
    color: "success" as const,
    icon: "tabler-mood-happy",
  },
]);

const getPlaceholder = (resourceName: string) => {
  const placeholderMap: Record<string, string> = {
    financial_resources: t(
      "umbrella-campaign.step-benefit.resources.placeholder.financial_resources",
    ),
    professional_growth: t(
      "umbrella-campaign.step-benefit.resources.placeholder.professional_growth",
    ),
    social_influence: t(
      "umbrella-campaign.step-benefit.resources.placeholder.social_influence",
    ),
    relationships: t(
      "umbrella-campaign.step-benefit.resources.placeholder.relationships",
    ),
    time_availability: t(
      "umbrella-campaign.step-benefit.resources.placeholder.time_availability",
    ),
    expertise: t(
      "umbrella-campaign.step-benefit.resources.placeholder.expertise",
    ),
    learning_ethics: t(
      "umbrella-campaign.step-benefit.resources.placeholder.learning_ethics",
    ),
    public_image: t(
      "umbrella-campaign.step-benefit.resources.placeholder.public_image",
    ),
    wellness: t(
      "umbrella-campaign.step-benefit.resources.placeholder.wellness",
    ),
  };

  return placeholderMap[resourceName] || "";
};

const isCompleted = computed(() => {
  return !!(resource.value?.text && resource.value?.label);
});

const regenerateResource = async () => {
  const { data: generated } =
    await UmbrellaCampaignsApi.askLucaForOneBuyerResource(
      brandId,
      projectId,
      umbrellaCampaignId.value,
      { bperson_resource_selected: resource.value },
    );

  setResourceValue({
    ...resource.value,
    ...generated.answer[resource.value.name],
  });

  return generated;
};
</script>

<template>
  <CardBase
    padding="sm"
    class="tw:flex tw:flex-col tw:gap-4 tw:p-4"
    :outlineColor="
      isCompleted ? 'success' : submitCount > 0 ? 'error' : 'default'
    "
  >
    <div>
      <h2 class="tw:mb-1.5 tw:text-lg tw:font-extrabold">
        {{
          t(
            `umbrella-campaign.step-benefit.resources.${resource.name}.display_name`,
          )
        }}
      </h2>

      <p class="tw:text-sm tw:text-secondary-text">
        {{
          t(
            `umbrella-campaign.step-benefit.resources.${resource.name}.description`,
          )
        }}
      </p>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-3">
      <div class="tw:flex tw:items-start tw:gap-2">
        <FieldTextarea
          :name="`${props.name}.text`"
          :placeholder="getPlaceholder(resource.name)"
          type="textarea"
          required
          :rows="3"
          class="tw:grow"
        />

        <ButtonGenerateIdea :fetcher="regenerateResource" square size="sm">
          {{ $t("forms.give-me-ideas.button") }}
        </ButtonGenerateIdea>
      </div>

      <div>
        <div class="tw:flex tw:flex-wrap tw:gap-2">
          <Button
            v-for="option in availabilityOptions"
            :key="option.value"
            :color="option.color"
            :variant="resource.label === option.value ? 'solid' : 'label'"
            size="sm"
            class="tw:grow tw:basis-0"
            type="button"
            :icon="option.icon"
            @click="resource.label = option.value"
          >
            {{ option.label }}
          </Button>
        </div>

        <FieldError v-if="submitCount > 0 && !resource.label">
          {{ $t("forms.required-field") }}
        </FieldError>
      </div>
    </div>
  </CardBase>
</template>
