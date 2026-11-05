<script lang="ts" setup>
const { t } = useI18n();
usePageTitle(() => t("routes.user-settings"));
</script>

<template>
  <!-- TODO: add help video URL later -->
  <PageTitle>
    {{ $t("settings.home.title") }}
  </PageTitle>

  <CardGrid>
    <SuggestionCard imageSrc="/images/emojis/man-police-officer.png">
      <template #title>
        {{ $t("settings.home.cards.card-security-title") }}
      </template>

      <template #description>
        {{ $t("settings.home.cards.card-security-description") }}
      </template>

      <template #action>
        <Button :to="{ name: 'UserSettingsSecurity' }">
          {{ $t("settings.home.cards.card-security-button-title") }}
        </Button>
      </template>
    </SuggestionCard>

    <PermissionGuard :requires="[{ name: 'ADMIN_ROLES', actions: ['R'] }]">
      <SuggestionCard imageSrc="/images/emojis/puzzle-piece.png">
        <template #title>
          {{ $t("settings.home.cards.card-roles-title") }}
        </template>

        <template #description>
          {{ $t("settings.home.cards.card-roles-description") }}
        </template>

        <template #action>
          <Button :to="{ name: 'UserSettingsRoles' }">
            {{ $t("settings.home.cards.card-roles-button-title") }}
          </Button>
        </template>
      </SuggestionCard>
    </PermissionGuard>

    <PermissionGuard :requires="[{ name: 'ADMIN_USER', actions: ['R'] }]">
      <SuggestionCard imageSrc="/images/emojis/briefcase.png">
        <template #title>
          {{ $t("settings.home.cards.card-users-title") }}
        </template>

        <template #description>
          {{ $t("settings.home.cards.card-users-description") }}
        </template>

        <template #action>
          <Button :to="{ name: 'UserSettingsUsers' }">
            {{ $t("settings.home.cards.card-users-button-title") }}
          </Button>
        </template>
      </SuggestionCard>
    </PermissionGuard>
  </CardGrid>
</template>
