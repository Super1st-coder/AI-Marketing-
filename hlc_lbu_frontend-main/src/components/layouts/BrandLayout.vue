<script lang="ts" setup>
const brandId = useBrandId();
const store = useBrandLayoutStore();
await store.initialize(brandId);

const logos = computed(() =>
  store.brand
    ? Array.isArray(store.brand.logos)
      ? store.brand.logos
      : store.brand.logos.values
    : [],
);

// Get the main logo
const mainLogo = computed(() =>
  logos.value.find((logo) => logo.category === "main-logo"),
);
const logoSrc = computed(() => mainLogo.value?.image_url ?? null);

const menuStore = useMenusStore();

const isUmbrellaCampaignModalOpen = ref(false);
const isCampaignModalOpen = ref(false);
const isFunnelModalOpen = ref(false);
const isApprovalsModalOpen = ref(false);
const isLaunchpadModalOpen = ref(false);
</script>

<template>
  <TopNav />

  <div class="tw:flex tw:min-h-[calc(100vh-66px)]">
    <Sidebar>
      <template #header>
        <div
          v-if="menuStore.isMenuVisuallyExpanded"
          class="tw:flex tw:items-center tw:gap-2"
        >
          <CardDynamicImage
            class="tw:aspect-square tw:w-8 tw:rounded-lg!"
            :src="logoSrc"
          />

          <h2 class="tw:font-semibold">{{ store.brand?.name }}</h2>
        </div>
      </template>

      <SidebarLinkWrapper>
        <SidebarLink :to="{ name: 'Brand' }" icon="tabler-home-filled">
          {{ $t("global.home") }}
        </SidebarLink>

        <SidebarLink :to="{ name: 'BrandInsights' }" icon="tabler-chart-bar">
          {{ $t("global.insights") }}
        </SidebarLink>
      </SidebarLinkWrapper>

      <SidebarLinkWrapper>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("global.foundation") }}
        </SidebarTitle>

        <SidebarLink :to="{ name: 'ProductList' }" icon="ion:cube">
          {{ $t("products.products") }}
        </SidebarLink>

        <SidebarLink
          :to="{ name: 'BuyerPersonList' }"
          icon="ic:round-people-alt"
        >
          {{ $t("buyer-person.target-customers") }}
        </SidebarLink>

        <Tooltip :disabled="!store.areProjectsDisabled" placement="bottom">
          <SidebarLink
            :to="{ name: 'ProjectList' }"
            icon="tabler-file-filled"
            :disabled="store.areProjectsDisabled"
          >
            {{ $t("projects.projects") }}
          </SidebarLink>

          <template #content>
            {{ $t("brands.home.disabled-tooltips.projects") }}
          </template>
        </Tooltip>
      </SidebarLinkWrapper>

      <SidebarLinkWrapper>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("global.strategy") }}
        </SidebarTitle>

        <Tooltip
          :disabled="!store.areUmbrellaCampaignsDisabled"
          placement="bottom"
        >
          <SidebarLink
            icon="tabler-umbrella-filled"
            @click="isUmbrellaCampaignModalOpen = true"
            :disabled="store.areUmbrellaCampaignsDisabled"
          >
            {{ $t("global.umbrella-campaigns") }}
          </SidebarLink>

          <template #content>
            {{ $t("brands.home.disabled-tooltips.umbrella-campaigns") }}
          </template>
        </Tooltip>

        <Tooltip :disabled="!store.areCampaignsDisabled" placement="bottom">
          <SidebarLink
            icon="tabler-speakerphone"
            @click="isCampaignModalOpen = true"
            :disabled="store.areCampaignsDisabled"
          >
            {{ $t("global.campaigns") }}
          </SidebarLink>

          <template #content>
            {{ $t("brands.home.disabled-tooltips.campaigns") }}
          </template>
        </Tooltip>

        <Tooltip :disabled="!store.areFunnelFlowsDisabled" placement="bottom">
          <SidebarLink
            icon="tabler:filter-filled"
            @click="isFunnelModalOpen = true"
            :disabled="store.areFunnelFlowsDisabled"
          >
            {{ $t("global.funnel") }}
          </SidebarLink>

          <template #content>
            {{ $t("brands.home.disabled-tooltips.funnels") }}
          </template>
        </Tooltip>
      </SidebarLinkWrapper>

      <SidebarLinkWrapper>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("global.launch") }}
        </SidebarTitle>

        <!-- Approvals hidden for now -->
        <!-- <Tooltip :disabled="!store.areFunnelFlowsDisabled" placement="bottom">
          <SidebarLink
            icon="custom:page-check"
            @click="isApprovalsModalOpen = true"
            :disabled="store.areFunnelFlowsDisabled"
          >
            {{ $t("global.approvals") }}
          </SidebarLink>

          <template #content>
            {{ $t("brands.home.disabled-tooltips.approvals") }}
          </template>
        </Tooltip> -->

        <Tooltip :disabled="!store.isLaunchpadDisabled" placement="bottom">
          <SidebarLink
            icon="custom:rocket"
            @click="isLaunchpadModalOpen = true"
            :disabled="store.isLaunchpadDisabled"
          >
            {{ $t("global.launchpad") }}
          </SidebarLink>

          <template #content>
            {{ $t("brands.home.disabled-tooltips.launchpad") }}
          </template>
        </Tooltip>
      </SidebarLinkWrapper>

      <template v-if="isLucaGuideEnabled">
        <Separator />

        <SidebarLinkWrapper>
          <SidebarLink :to="{ name: 'LucaGuide' }" icon="tabler:compass">
            {{ $t("global.luca-guide") }}
            <span
              class="tw:ml-2 tw:inline-block tw:rounded-md tw:bg-primary-100 tw:px-1.5 tw:py-0.5 tw:align-middle tw:text-[10px] tw:font-semibold tw:tracking-wide tw:text-primary tw:uppercase"
            >
              {{ $t("global.beta") }}
            </span>
          </SidebarLink>
        </SidebarLinkWrapper>
      </template>

      <template #footer>
        <SidebarLinkWrapper>
          <SidebarLink
            :to="{ name: 'BrandSettings' }"
            icon="tabler-settings-filled"
          >
            {{ $t("settings.title") }}
          </SidebarLink>
        </SidebarLinkWrapper>
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

    <ModalGoToUmbrellaCampaign v-model="isUmbrellaCampaignModalOpen" />
    <ModalGoToCampaign v-model="isCampaignModalOpen" />
    <ModalGoToFunnel v-model="isFunnelModalOpen" />
    <ModalGoToApprovals v-model="isApprovalsModalOpen" />
    <ModalGoToLaunchpad v-model="isLaunchpadModalOpen" />
  </div>
</template>
