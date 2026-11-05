<script lang="ts" setup>
import CampaignsApi from "@/services/projects/CampaignsApi";

const brandId = useBrandId();
const projectId = useProjectId();

const campaignId = useCampaignId();
const campaign = (await CampaignsApi.getOne(brandId, projectId, campaignId))
  .data;
</script>

<template>
  <TopNav />

  <div class="tw:flex tw:min-h-[calc(100vh-66px)]">
    <Sidebar>
      <template #header>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("global.campaign") }}
        </SidebarTitle>
        <SidebarTitle class="tw:text-2xl tw:font-extrabold tw:text-pretty">
          {{ campaign.name }}
        </SidebarTitle>
      </template>

      <SidebarLinkWrapper>
        <SidebarLink :to="{ name: 'FunnelFlowHome' }" icon="tabler-umbrella">
          Funnel Flow
        </SidebarLink>
      </SidebarLinkWrapper>

      <template #footer>
        <SidebarLink
          :to="{ name: 'CampaignSettings' }"
          variant="link"
          icon="tabler-arrow-left"
        >
          {{
            $t("campaigns.back-to-campaign-with-name", {
              name: campaign.name,
            })
          }}
        </SidebarLink>
      </template>
    </Sidebar>

    <GradientBackground class="tw:w-full">
      <main class="tw:h-full">
        <ContainerDashboard>
          <RouterView v-slot="{ Component }">
            <Suspense suspensible :timeout="0">
              <component :is="Component"></component>

              <template #fallback>
                <CircleLoaderDefault class="tw:h-full" />
              </template>
            </Suspense>
          </RouterView>
        </ContainerDashboard>
      </main>
    </GradientBackground>
  </div>
</template>
