<script lang="ts" setup>
const { t } = useI18n();
usePageTitle(() => t("routes.no-access"));
</script>

<template>
  <Container class="tw:flex tw:min-h-screen tw:items-center tw:justify-center">
    <CardBase class="tw:p-6 tw:lg:p-12">
      <CardTitle icon="tabler-alert-circle" iconVariant="error" class="tw:mb-4">
        {{ $t("brands.no-access.title") }}
      </CardTitle>

      <CardParagraph>
        {{ $t("brands.no-access.description") }}
      </CardParagraph>
    </CardBase>
  </Container>
</template>
