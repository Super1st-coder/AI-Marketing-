<script lang="ts" setup>
const authStore = useAuthStore();
</script>

<template>
  <TopNav />

  <div class="tw:flex tw:min-h-[calc(100vh-66px)]">
    <Sidebar>
      <template #header>
        <SidebarTitle variant="secondary" size="sm">
          {{ $t("settings.title") }}
        </SidebarTitle>

        <SidebarTitle class="tw:text-2xl tw:font-extrabold tw:text-pretty">
          {{ authStore.userFullname }}
        </SidebarTitle>
      </template>

      <SidebarLinkWrapper>
        <SidebarLink :to="{ name: 'UserSettings' }" icon="tabler-home">
          {{ $t("global.home") }}
        </SidebarLink>

        <SidebarLink
          :to="{ name: 'UserSettingsSecurity' }"
          icon="tabler:user-shield"
        >
          {{ $t("global.security") }}
        </SidebarLink>

        <PermissionGuard :requires="[{ name: 'ADMIN_ROLES', actions: ['R'] }]">
          <SidebarLink :to="{ name: 'UserSettingsRoles' }" icon="tabler:puzzle">
            {{ $t("global.roles") }}
          </SidebarLink>
        </PermissionGuard>

        <PermissionGuard :requires="[{ name: 'ADMIN_ORG', actions: ['R'] }]">
          <SidebarLink
            :to="{ name: 'UserSettingsOrganizations' }"
            icon="tabler:building"
          >
            {{ $t("global.organizations") }}
          </SidebarLink>
        </PermissionGuard>

        <PermissionGuard :requires="[{ name: 'ADMIN_USER', actions: ['R'] }]">
          <SidebarLink
            :to="{ name: 'UserSettingsUsers' }"
            icon="ic:round-people-alt"
          >
            {{ $t("global.users") }}
          </SidebarLink>
        </PermissionGuard>
      </SidebarLinkWrapper>

      <template #footer>
        <SidebarLink
          :to="{ name: 'BrandList' }"
          variant="link"
          icon="tabler-arrow-left"
        >
          {{ $t("brands.return-to-brands") }}
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
