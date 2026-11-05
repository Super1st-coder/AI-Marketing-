<script lang="ts" setup>
const brandId = useBrandId();
const store = useLucaGuideLayoutStore();
const route = useRoute();
const router = useRouter();

function getOnboardingRedirect(name: typeof route.name) {
  if (!store.isOnboardingCompleted && name !== "LucaGuideOnboarding") {
    return { name: "LucaGuideOnboarding" as const };
  }
}

await store.initialize(brandId);

const redirect = getOnboardingRedirect(route.name);
if (redirect) {
  await router.replace(redirect);
}

onBeforeRouteUpdate((to) => getOnboardingRedirect(to.name));
</script>

<template>
  <TopNav />

  <div class="tw:flex tw:min-h-[calc(100vh-66px)]">
    <Sidebar>
      <template #header>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("global.luca-guide") }}
        </SidebarTitle>

        <SidebarTitle class="tw:text-2xl tw:font-extrabold tw:text-pretty">
          {{ store.brand?.name }}
        </SidebarTitle>
      </template>

      <SidebarLinkWrapper v-if="!store.isOnboardingCompleted">
        <SidebarLink
          :to="{ name: 'LucaGuideOnboarding' }"
          :ringLoader="{
            steps: store.totalOnboardingSteps,
            completedSteps: store.completedOnboardingSteps,
          }"
        >
          {{ $t("luca-guide.get-started") }}
        </SidebarLink>
      </SidebarLinkWrapper>

      <SidebarLinkWrapper>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("luca-guide.overview") }}
        </SidebarTitle>

        <SidebarLink
          :to="{ name: 'LucaGuide' }"
          icon="tabler:home-2"
          :disabled="!store.isOnboardingCompleted"
        >
          {{ $t("luca-guide.home.label") }}
        </SidebarLink>

        <SidebarLink
          :to="{ name: 'LucaGuideCampaigns' }"
          icon="tabler:speakerphone"
          :exact="false"
          :disabled="!store.isOnboardingCompleted"
        >
          {{ $t("luca-guide.campaigns.label") }}
        </SidebarLink>
      </SidebarLinkWrapper>

      <SidebarLinkWrapper>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("luca-guide.decide") }}
        </SidebarTitle>

        <SidebarLink icon="tabler:inbox" disabled>
          {{ $t("luca-guide.creative-decision-inbox") }}
        </SidebarLink>

        <SidebarLink icon="tabler:test-pipe" disabled>
          {{ $t("luca-guide.creative-performance-lab") }}
        </SidebarLink>
      </SidebarLinkWrapper>

      <SidebarLinkWrapper>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("luca-guide.produce-and-test") }}
        </SidebarTitle>

        <SidebarLink icon="tabler:clipboard" disabled>
          {{ $t("luca-guide.plan") }}
        </SidebarLink>

        <SidebarLink icon="tabler:flask" disabled>
          {{ $t("luca-guide.experiments") }}
        </SidebarLink>

        <SidebarLink icon="tabler:history" disabled>
          {{ $t("luca-guide.history") }}
        </SidebarLink>
      </SidebarLinkWrapper>

      <SidebarLinkWrapper>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("luca-guide.knowledge") }}
        </SidebarTitle>

        <SidebarLink icon="tabler:school" disabled>
          {{ $t("luca-guide.learnings") }}
        </SidebarLink>
      </SidebarLinkWrapper>

      <template #footer>
        <SidebarLinkWrapper class="tw:w-full">
          <SidebarLink
            v-if="store.isOnboardingCompleted"
            :to="{ name: 'LucaGuideSettings' }"
            icon="tabler:settings-filled"
          >
            {{ $t("luca-guide.settings") }}
          </SidebarLink>

          <SidebarLink icon="tabler:help-circle" disabled>
            {{ $t("luca-guide.help") }}
          </SidebarLink>

          <SidebarLink
            :to="{ name: 'Brand' }"
            variant="link"
            icon="tabler-arrow-left"
          >
            {{ $t("luca-guide.back-to-workplace") }}
          </SidebarLink>
        </SidebarLinkWrapper>
      </template>
    </Sidebar>

    <GradientBackground class="tw:w-full tw:min-w-0">
      <main class="tw:h-full">
        <RouterView v-slot="{ Component, route }">
          <!-- Key by route.path so navigating between pages that resolve to the SAME component
               (e.g. campaign A → campaign B, or re-entering the performance page after editing
               its North Star) remounts the page and re-runs its <script setup> data fetch,
               instead of reusing the instance and showing stale data. Mirrors AddGenerationLayout. -->
          <Suspense :key="route.path" suspensible :timeout="0">
            <component :is="Component"></component>

            <template #fallback>
              <CircleLoaderDefault class="tw:h-full" />
            </template>
          </Suspense>
        </RouterView>
      </main>
    </GradientBackground>
  </div>
</template>
