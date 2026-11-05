<script setup lang="ts">
import {
  AdByCampaignDefinitionData,
  AdChannelDefinition,
} from "@/services/funnel-flow/paid-social/AdsApi";
import { AdsExperimentByAdSetData } from "@/services/funnel-flow/paid-social/AdsExperiment";
import { AudiencesByChannel } from "@/services/projects/AudienceApi";

const props = defineProps<{
  joinedData: {
    audiences: AudiencesByChannel[];
    experiment: AdsExperimentByAdSetData;
    ads: AdByCampaignDefinitionData[];
    id: number;
    name: string;
  }[];
}>();

const emit = defineEmits<{
  getChannel: [
    channel: AdChannelDefinition,
    adSetIndex: string,
    adIndex: string,
  ];
}>();
</script>

<template>
  <div
    class="tw:grid tw:grid-cols-1 tw:items-start tw:gap-4 tw:lg:grid-cols-2 tw:xl:grid-cols-3"
  >
    <div
      v-for="set in props.joinedData"
      class="tw:rounded-[20px] tw:bg-[#2F2B3D14] tw:p-2"
    >
      <div class="tw:flex tw:gap-2 tw:px-1.5 tw:pt-2 tw:pb-4">
        <Icon icon="tabler-layout-2" class="tw:text-2xl tw:text-primary" />

        <h4 class="tw:font-bold">
          {{ set.name }}
        </h4>
      </div>

      <div class="tw:overflow-hidden tw:rounded-xl tw:bg-white">
        <AccordionList variant="solid">
          <template v-for="audience in set.audiences">
            <Accordion
              v-if="audience.preferred_audience"
              :title="
                $t(
                  'funnel-flow.paid-social.summary.sets.audiences.title',

                  { channel: audience.channel_name },
                )
              "
              openByDefault
            >
              <AudiencePreview
                :audience="audience.preferred_audience"
                :showTitle="true"
                audienceType="preferred"
                class="tw:p-0!"
              />
            </Accordion>
          </template>

          <Accordion
            :title="$t('funnel-flow.paid-social.summary.sets.experiment.title')"
            openByDefault
          >
            <p class="tw:mb-4 tw:text-sm tw:capitalize">
              <strong>{{
                $t("funnel-flow.paid-social.summary.sets.experiment.type-title")
              }}</strong>

              {{
                $t(
                  `funnel-flow.paid-social.creative-angle.formats.${set.experiment.type}.title`,
                )
              }}
            </p>

            <p class="tw:mb-4 tw:text-sm">
              <strong>{{
                $t(
                  "funnel-flow.paid-social.summary.sets.experiment.category-title",
                )
              }}</strong>

              {{
                $te(
                  `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(set.experiment.subcategory.category.name)}.name`,
                )
                  ? $t(
                      `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(set.experiment.subcategory.category.name)}.name`,
                    )
                  : set.experiment.subcategory.category.name
              }}
              /
              {{
                $te(
                  `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(set.experiment.subcategory.name)}.name`,
                )
                  ? $t(
                      `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(set.experiment.subcategory.name)}.name`,
                    )
                  : set.experiment.subcategory.name
              }}
            </p>

            <p class="tw:text-sm tw:text-gray-500">
              {{
                $te(
                  `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(set.experiment.subcategory.name)}.description`,
                )
                  ? $t(
                      `funnel-flow.paid-social.creative-angle.subcategories.${toI18nKeySegment(set.experiment.subcategory.name)}.description`,
                    )
                  : set.experiment.subcategory.description
              }}
            </p>
          </Accordion>

          <Accordion
            :title="$t('funnel-flow.paid-social.summary.sets.ads.title')"
          >
            <div>
              <template v-for="(ad, index) in set.ads">
                <template v-for="channel in ad.ad_channels">
                  <AdsetsSummaryFormatRow
                    :ad="ad"
                    :channel="channel"
                    @click="
                      () => emit('getChannel', channel, set.name, ad.ad_name)
                    "
                  />
                </template>

                <Separator v-if="index !== set.ads.length - 1" />
              </template>
            </div>
          </Accordion>
        </AccordionList>
      </div>
    </div>
  </div>
</template>

<style></style>
