<script setup lang="ts">
import { CampaignFormData } from "./CampaignForm.vue";
import { buildMetricsSummaryText } from "./campaignSummaryMetrics";

const props = defineProps<{
  campaign: CampaignFormData;
  bpersonName: string;
  productName: string;
  editable?: boolean;
}>();

// When the AI-generated summary text for a metric group is missing/empty, fall
// back to the structured metrics saved in the KPIs step so the values still
// render (HL-2684 — Campaign KPIs showed blank even though metrics were saved).
const campaignGoalsText = computed(
  () =>
    props.campaign.summary_saved?.campaign.campaign_goals ||
    props.campaign.summary_generated?.campaign.campaign_goals ||
    buildMetricsSummaryText(props.campaign, "Goals") ||
    "Text not available",
);
const campaignResourcesText = computed(
  () =>
    props.campaign.summary_saved?.campaign.campaign_resources ||
    props.campaign.summary_generated?.campaign.campaign_resources ||
    buildMetricsSummaryText(props.campaign, "Resources") ||
    "Text not available",
);
const campaignKpisText = computed(
  () =>
    props.campaign.summary_saved?.campaign.campaign_kpis ||
    props.campaign.summary_generated?.campaign.campaign_kpis ||
    buildMetricsSummaryText(props.campaign, "Marketing") ||
    "Text not available",
);
</script>

<template>
  <!-- Buyer Person-->
  <div class="tw:flex tw:flex-col tw:gap-8 tw:lg:flex-row">
    <div class="tw:flex tw:w-full tw:flex-col tw:gap-5">
      <h2 class="tw:line-clamp-1 tw:text-lg tw:font-extrabold">
        {{ bpersonName }}
      </h2>

      <CardDynamicImage
        :src="campaign.bperson_thumbnail_url ?? undefined"
        class="tw:aspect-square"
      />

      <AccordionList>
        <AccordionWithEditableText
          v-if="editable"
          name="bperson.persona_profile"
          :title="$t('campaigns.summary.accordion.personaprofiletitle')"
          icon="tabler-user"
          variant="primary"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.personaprofiletitle')"
          icon="tabler-user"
          iconVariant="primary"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.bperson.persona_profile ??
              campaign.summary_generated?.bperson.persona_profile ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="bperson.persona_challenges"
          :title="$t('campaigns.summary.accordion.personachallengestitle')"
          icon="tabler-heart-broken"
          variant="info"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.personachallengestitle')"
          icon="tabler-heart-broken"
          iconVariant="info"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.bperson.persona_challenges ??
              campaign.summary_generated?.bperson.persona_challenges ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="bperson.persona_journey"
          :title="$t('campaigns.summary.accordion.personajourneytitle')"
          icon="tabler:route"
          variant="error"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.personajourneytitle')"
          icon="tabler:route"
          iconVariant="error"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.bperson.persona_journey ??
              campaign.summary_generated?.bperson.persona_journey ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="bperson.persona_motivation"
          :title="$t('campaigns.summary.accordion.personamotivationtitle')"
          icon="tabler-bulb"
          variant="success"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.personamotivationtitle')"
          icon="tabler-bulb"
          iconVariant="success"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.bperson.persona_motivation ??
              campaign.summary_generated?.bperson.persona_motivation ??
              "Text not available"
            }}
          </p>
        </Accordion>
      </AccordionList>
    </div>

    <!-- Campaña-->
    <div class="tw:flex tw:w-full tw:flex-col tw:gap-5">
      <h2 class="tw:line-clamp-1 tw:text-lg tw:font-extrabold">
        {{ campaign.name ?? "Title not available" }}
      </h2>

      <CardDynamicImage
        :src="props.campaign.thumbnail_url"
        class="tw:aspect-square"
      />

      <AccordionList>
        <AccordionWithEditableText
          v-if="editable"
          name="campaign.campaign_concept_timing"
          :title="$t('campaigns.summary.accordion.concepttimingtitle')"
          icon="tabler:clipboard-list"
          variant="primary"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.concepttimingtitle')"
          icon="tabler:clipboard-list"
          iconVariant="primary"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.campaign.campaign_concept_timing ??
              campaign.summary_generated?.campaign.campaign_concept_timing ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="campaign.campaign_goals"
          :title="$t('campaigns.summary.accordion.goalstitle')"
          icon="tabler:target"
          variant="info"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.goalstitle')"
          icon="tabler:target"
          iconVariant="info"
        >
          <p class="tw:whitespace-pre-wrap">
            {{ campaignGoalsText }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="campaign.campaign_resources"
          :title="$t('campaigns.summary.accordion.resourcestitle')"
          icon="mdi:toolbox"
          variant="primary"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.resourcestitle')"
          icon="mdi:toolbox"
          iconVariant="primary"
        >
          <p class="tw:whitespace-pre-wrap">
            {{ campaignResourcesText }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="campaign.campaign_kpis"
          :title="$t('campaigns.summary.accordion.kpistitle')"
          icon="octicon:graph-16"
          variant="success"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.kpistitle')"
          icon="octicon:graph-16"
          iconVariant="success"
        >
          <p class="tw:whitespace-pre-wrap">
            {{ campaignKpisText }}
          </p>
        </Accordion>
      </AccordionList>
    </div>

    <!-- Product -->
    <div class="tw:flex tw:w-full tw:flex-col tw:gap-5">
      <h2 class="tw:line-clamp-1 tw:text-lg tw:font-extrabold">
        {{ productName }}
      </h2>

      <CardDynamicImage
        :src="campaign.product_thumbnail_url ?? undefined"
        class="tw:aspect-square"
      />

      <AccordionList>
        <AccordionWithEditableText
          v-if="editable"
          name="product.core_incentive_offer"
          :title="$t('campaigns.summary.accordion.incentiveoffertitle')"
          icon="tabler-gift"
          variant="primary"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.incentiveoffertitle')"
          icon="tabler-gift"
          iconVariant="primary"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.product.core_incentive_offer ??
              campaign.summary_generated?.product.core_incentive_offer ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="product.problem_solution_fit"
          :title="$t('campaigns.summary.accordion.solutionfittitle')"
          icon="tabler-puzzle"
          variant="error"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.solutionfittitle')"
          icon="tabler-puzzle"
          iconVariant="error"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.product.problem_solution_fit ??
              campaign.summary_generated?.product.problem_solution_fit ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="product.unique_value_proposition"
          :title="$t('campaigns.summary.accordion.valuepropositiontitle')"
          icon="tabler-star"
          variant="info"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.valuepropositiontitle')"
          icon="tabler-star"
          iconVariant="info"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.product.unique_value_proposition ??
              campaign.summary_generated?.product.unique_value_proposition ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="product.emotional_outcome_payoff"
          :title="$t('campaigns.summary.accordion.emotionaltitle')"
          icon="tabler:mood-smile-filled"
          variant="success"
          editable
        />
        <Accordion
          v-else
          :title="$t('campaigns.summary.accordion.emotionaltitle')"
          icon="tabler:mood-smile-filled"
          iconVariant="success"
        >
          <p class="tw:whitespace-pre-wrap">
            {{
              campaign.summary_saved?.product.emotional_outcome_payoff ??
              campaign.summary_generated?.product.emotional_outcome_payoff ??
              "Text not available"
            }}
          </p>
        </Accordion>
      </AccordionList>
    </div>
  </div>
</template>
