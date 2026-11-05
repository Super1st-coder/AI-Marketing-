<script setup lang="ts">
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import LucaGuideDashboardApi from "@/services/guide/LucaGuideDashboardApi";

const store = useLucaGuideLayoutStore();
const { t } = useI18n();

usePageTitle(() => t("routes.luca-guide", { brand: store.brand?.name ?? "" }));

const [homeSummary, campaigns, recentActivity] = await Promise.all([
  LucaGuideCampaignsApi.getHomeSummary(),
  LucaGuideCampaignsApi.list(),
  LucaGuideDashboardApi.getRecentActivity(),
]);

const activeCampaignsCount = homeSummary.active_campaigns;
const pendingSetupCount = homeSummary.pending_setup;
const opportunityCount = homeSummary.opportunity;
const requiresAttentionCount = homeSummary.requires_attention;
</script>

<template>
  <ContainerDashboard>
    <PageTitle>
      {{ $t("luca-guide.home.title") }}
      <template #description>
        {{ $t("luca-guide.home.description") }}
      </template>
    </PageTitle>

    <div class="tw:flex tw:flex-col tw:gap-5">
      <div class="tw:grid tw:grid-cols-2 tw:gap-4 tw:lg:grid-cols-4">
        <LucaGuideHomeStatCard
          :label="$t('luca-guide.home.stats.active-campaigns')"
          :value="activeCampaignsCount"
        />

        <LucaGuideHomeStatCard
          :label="$t('luca-guide.home.stats.pending-setup')"
          :value="pendingSetupCount"
          color="warning"
        />

        <LucaGuideHomeStatCard
          :label="$t('luca-guide.home.stats.opportunity')"
          :value="opportunityCount"
          color="success"
        />

        <LucaGuideHomeStatCard
          :label="$t('luca-guide.home.stats.requires-attention')"
          :value="requiresAttentionCount"
          color="error"
        />
      </div>

      <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:lg:grid-cols-3">
        <LucaGuideHomeCampaigns
          class="tw:lg:col-span-2"
          :campaigns="campaigns"
        />

        <LucaGuideHomeRecentActivity :activities="recentActivity" />
      </div>

      <!-- TODO: Enable suggestion card links once the routes exist -->
      <div
        class="tw:grid tw:grid-cols-1 tw:gap-4 tw:md:grid-cols-2 tw:xl:grid-cols-4"
      >
        <SuggestionCard icon="tabler:inbox" disabled class="tw:h-full">
          <template #title>
            {{ $t("luca-guide.home.cards.creative-decision-inbox.title") }}
          </template>

          <template #description>
            {{
              $t("luca-guide.home.cards.creative-decision-inbox.description")
            }}
          </template>

          <template #link>
            <Link is="button" disabled icon="tabler-arrow-narrow-right">
              {{ $t("luca-guide.home.cards.creative-decision-inbox.link") }}
            </Link>
          </template>
        </SuggestionCard>

        <SuggestionCard icon="tabler:wand" disabled class="tw:h-full">
          <template #title>
            {{ $t("luca-guide.home.cards.creative-performance-lab.title") }}
          </template>

          <template #description>
            {{
              $t("luca-guide.home.cards.creative-performance-lab.description")
            }}
          </template>

          <template #link>
            <Link is="button" disabled icon="tabler-arrow-narrow-right">
              {{ $t("luca-guide.home.cards.creative-performance-lab.link") }}
            </Link>
          </template>
        </SuggestionCard>

        <SuggestionCard icon="tabler:archive" disabled class="tw:h-full">
          <template #title>
            {{ $t("luca-guide.home.cards.experiments-batch.title") }}
          </template>

          <template #description>
            {{ $t("luca-guide.home.cards.experiments-batch.description") }}
          </template>

          <template #link>
            <Link is="button" disabled icon="tabler-arrow-narrow-right">
              {{ $t("luca-guide.home.cards.experiments-batch.link") }}
            </Link>
          </template>
        </SuggestionCard>

        <SuggestionCard icon="tabler:flask" disabled class="tw:h-full">
          <template #title>
            {{ $t("luca-guide.home.cards.experiments.title") }}
          </template>

          <template #description>
            {{ $t("luca-guide.home.cards.experiments.description") }}
          </template>

          <template #link>
            <Link is="button" disabled icon="tabler-arrow-narrow-right">
              {{ $t("luca-guide.home.cards.experiments.link") }}
            </Link>
          </template>
        </SuggestionCard>
      </div>
    </div>
  </ContainerDashboard>
</template>
