<script lang="ts" setup>
import CampaignsApi from "@/services/projects/CampaignsApi";
import { CampaignConcept } from "./schemas";

interface Props {
  name: string;
  selected?: boolean;
  brandId: number;
  projectId: number;
  campaignId: number;
}

const props = defineProps<Props>();
const isExpanded = defineModel<boolean>("expanded");
const emits = defineEmits<{
  (e: "checked", checked: boolean): void;
}>();

const { value: model, setValue } = useField<CampaignConcept>(props.name);
const { value: preferred } = useField<number>(`${props.name}.preferred`);

const isSelected = computed({
  get: () => preferred.value === 1,
  set: (value) => {
    preferred.value = value ? 1 : 0;
    emits("checked", preferred.value === 1);
  },
});

const askLucaFetcher = async (text: string) => {
  const response = await CampaignsApi.askLucaForOneCampaign(
    props.brandId,
    props.projectId,
    props.campaignId,
    { text, campaign_selected: model.value },
  );

  setValue({
    ...response.data.answer,
    id: model.value.id,
    preferred: model.value.preferred,
  });

  return response.data.answer;
};
</script>

<template>
  <SelectableCard
    v-model:selected="isSelected"
    expandable
    v-model:expanded="isExpanded"
    colorSelectedClass="tw:border-transparent tw:bg-success"
    variant="success"
  >
    <template #header>
      <FieldEditableText
        :name="`${props.name}.campaign.title`"
        v-model="model.campaign.title"
        required
        class="tw:mb-1 tw:text-lg tw:leading-tight tw:font-extrabold"
        variant="text"
      />
    </template>

    <FieldEditableText
      :name="`${props.name}.sections.short_description.text`"
    />

    <button class="tw:flex tw:flex-col tw:gap-5 tw:text-left" type="button">
      <template v-if="isExpanded">
        <AccordionList>
          <Accordion
            :title="$t('campaigns.conceptcard.accordion.campaign-details')"
            icon="tabler-speakerphone"
            iconVariant="primary"
          >
            <FieldEditableText
              :name="`${props.name}.sections.campaign_details.text`"
            />
          </Accordion>

          <Accordion
            :title="$t('campaigns.conceptcard.accordion.execution-steps')"
            icon="tabler-settings"
            iconVariant="gray"
          >
            <FieldEditableText
              :name="`${props.name}.sections.execution_steps.text`"
            />
          </Accordion>

          <Accordion
            :title="$t('campaigns.conceptcard.accordion.creative-types')"
            icon="tabler-palette"
            iconVariant="primary"
          >
            <FieldEditableText
              :name="`${props.name}.sections.creative_types.text`"
            />
          </Accordion>

          <Accordion
            :title="$t('campaigns.conceptcard.accordion.funnel-flow')"
            icon="tabler-filter"
            iconVariant="info"
          >
            <FieldEditableText
              :name="`${props.name}.sections.funnel_flow.text`"
            />
          </Accordion>

          <Accordion
            :title="$t('campaigns.conceptcard.accordion.budget-effort')"
            icon="tabler-coin"
            iconVariant="success"
          >
            <FieldEditableText :name="`${props.name}.sections.budget.text`" />
          </Accordion>
          <Accordion
            :title="$t('campaigns.conceptcard.accordion.cta')"
            icon="tabler-bell-ringing"
            iconVariant="error"
          >
            <FieldEditableText :name="`${props.name}.sections.cta.text`" />
          </Accordion>
        </AccordionList>

        <ButtonGenerateIdea
          v-if="isExpanded"
          :fetcher="askLucaFetcher"
          useText
          color="primary"
          size="sm"
          variant="outlined"
          class="tw:bg-white"
          :textLabel="$t('campaigns.conceptcard.ask-luca.textLabel')"
          :textPlaceholder="
            $t('campaigns.conceptcard.ask-luca.textPlaceholder')
          "
        >
          <template #title
            >{{ $t("campaigns.conceptcard.ask-luca.title") }}
          </template>

          <template #description>
            {{ $t("campaigns.conceptcard.ask-luca.description") }}
          </template>

          <template #submit>
            {{ $t("campaigns.conceptcard.ask-luca.submit") }}
          </template>
        </ButtonGenerateIdea>
      </template>
    </button>
  </SelectableCard>
</template>
