<script lang="ts" setup>
import BrandsApi from "@/services/BrandsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";

const brandId = useBrandId();
const brand = (await BrandsApi.getOne(brandId)).data;

const projectId = useProjectId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;
</script>

<template>
  <TopNav />

  <div class="tw:flex tw:min-h-[calc(100vh-66px)]">
    <Sidebar>
      <template #header>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("projects.project") }}
        </SidebarTitle>

        <SidebarTitle class="tw:text-2xl tw:font-extrabold tw:text-pretty">
          {{ project.name }}
        </SidebarTitle>
      </template>

      <SidebarLinkWrapper>
        <!-- <SidebarLink
          :to="{ name: 'CreativeConceptList' }"
          icon="tabler-palette"
        >
          Creative concepts
        </SidebarLink> -->

        <SidebarLink
          :to="{ name: 'UmbrellaCampaignList' }"
          icon="tabler-umbrella"
        >
          Umbrella Campaigns
        </SidebarLink>

        <SidebarLink :to="{ name: 'CampaignList' }" icon="tabler-speakerphone">
          Campaigns
        </SidebarLink>
      </SidebarLinkWrapper>

      <template #footer>
        <SidebarLink
          :to="{ name: 'ProjectList' }"
          variant="link"
          icon="tabler-arrow-left"
        >
          {{ $t("brands.back-to-brand", { name: brand.name }) }}
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
