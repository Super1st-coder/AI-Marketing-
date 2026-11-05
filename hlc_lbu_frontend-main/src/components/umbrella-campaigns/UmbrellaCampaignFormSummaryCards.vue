<script setup lang="ts">
import { UmbrellaCampaignData } from "@/services/projects/UmbrellaCampaignsApi";

const props = defineProps<{
  umbrellaCampaign: UmbrellaCampaignData;
  editable?: boolean;
}>();
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-8 tw:lg:flex-row">
    <div class="tw:flex tw:w-full tw:flex-col tw:gap-5">
      <h2 class="tw:line-clamp-1 tw:text-lg tw:font-extrabold">
        {{ umbrellaCampaign?.bperson?.name }}
      </h2>

      <CardDynamicImage
        class="tw:aspect-square"
        :src="props.umbrellaCampaign?.bperson?.thumbnail_url ?? undefined"
      />

      <AccordionList>
        <AccordionWithEditableText
          v-if="editable"
          name="story_hero"
          :title="$t('umbrella-campaign.step-summary.hero-title')"
          icon="tabler-crown"
          variant="primary"
          editable
          required
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.hero-title')"
          icon="tabler-crown"
          iconVariant="primary"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_persona.find(
                (item) => item.id === "hero_story",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_persona.find(
                (item) => item.id === "hero_story",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="target_customer"
          :title="$t('umbrella-campaign.step-summary.customer-reality-title')"
          icon="tabler-user"
          variant="info"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.customer-reality-title')"
          icon="tabler-user"
          iconVariant="info"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_persona.find(
                (item) => item.id === "customer_reality",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_persona.find(
                (item) => item.id === "customer_reality",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="who_reaching"
          :title="$t('umbrella-campaign.step-summary.emotional-conflict-title')"
          icon="tabler-pin"
          variant="success"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.emotional-conflict-title')"
          icon="tabler-pin"
          iconVariant="success"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_persona.find(
                (item) => item.id === "emotional_conflict",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_persona.find(
                (item) => item.id === "emotional_conflict",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>
      </AccordionList>
    </div>

    <!-- Componente Concepto Creativo -->
    <div class="tw:flex tw:w-full tw:flex-col tw:gap-5">
      <h2 class="tw:line-clamp-1 tw:text-lg tw:font-extrabold">
        {{
          umbrellaCampaign?.name ??
          $t("campaigns.select-umbrella-campaign.titlenotavailablecardtext")
        }}
      </h2>

      <CardDynamicImage
        class="tw:aspect-square"
        :src="umbrellaCampaign?.thumbnail_url ?? undefined"
      />

      <AccordionList>
        <AccordionWithEditableText
          v-if="editable"
          name="big_idea"
          :title="$t('umbrella-campaign.step-summary.big-idea-title')"
          icon="tabler-bulb"
          variant="primary"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.big-idea-title')"
          icon="tabler-bulb"
          iconVariant="primary"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_creative_concept.find(
                (item) => item.id === "big_idea",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_creative_concept.find(
                (item) => item.id === "big_idea",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="message"
          :title="$t('umbrella-campaign.step-summary.core-message-title')"
          icon="tabler-message"
          variant="info"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.core-message-title')"
          icon="tabler-message"
          iconVariant="info"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_creative_concept.find(
                (item) => item.id === "core_message",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_creative_concept.find(
                (item) => item.id === "core_message",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="hook"
          :title="$t('umbrella-campaign.step-summary.hook-title')"
          icon="tabler-magnet"
          variant="error"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.hook-title')"
          icon="tabler-magnet"
          iconVariant="error"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_creative_concept.find(
                (item) => item.id === "hook",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_creative_concept.find(
                (item) => item.id === "hook",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>
      </AccordionList>
    </div>

    <div class="tw:flex tw:w-full tw:flex-col tw:gap-5">
      <h2 class="tw:line-clamp-1 tw:text-lg tw:font-extrabold">
        {{ umbrellaCampaign?.product?.name }}
      </h2>

      <CardDynamicImage
        :src="props.umbrellaCampaign?.product?.thumbnail_url ?? undefined"
        class="tw:aspect-square"
      />

      <AccordionList>
        <AccordionWithEditableText
          v-if="editable"
          name="product_role"
          :title="$t('umbrella-campaign.step-summary.product-role-title')"
          icon="ion:cube"
          variant="primary"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.product-role-title')"
          icon="ion:cube"
          iconVariant="primary"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_product.find(
                (item) => item.id === "concept_reality_resonance",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_product.find(
                (item) => item.id === "concept_reality_resonance",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="how_product_shines"
          :title="$t('umbrella-campaign.step-summary.how-product-shines-title')"
          icon="tabler-star"
          variant="info"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.how-product-shines-title')"
          icon="tabler-star"
          iconVariant="info"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_product.find(
                (item) => item.id === "customer_journey",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_product.find(
                (item) => item.id === "customer_journey",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>

        <AccordionWithEditableText
          v-if="editable"
          name="solution"
          :title="$t('umbrella-campaign.step-summary.solution-title')"
          icon="tabler-puzzle"
          variant="error"
          editable
        />
        <Accordion
          v-else
          :title="$t('umbrella-campaign.step-summary.solution-title')"
          icon="tabler-puzzle"
          iconVariant="error"
        >
          <p>
            {{
              umbrellaCampaign?.summary_saved?.the_product.find(
                (item) => item.id === "solution",
              )?.content ??
              umbrellaCampaign?.summary_generated?.the_product.find(
                (item) => item.id === "solution",
              )?.content ??
              "Text not available"
            }}
          </p>
        </Accordion>
      </AccordionList>
    </div>
  </div>
</template>
