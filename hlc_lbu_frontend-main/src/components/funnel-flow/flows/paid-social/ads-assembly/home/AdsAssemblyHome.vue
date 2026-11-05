<script setup lang="ts">
const store = useFunnelPaidSocialAdsAssemblyStore();
</script>

<template>
  <FormStepLayout as="div" :maxWidth="870">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=r1462xlXJOQ"
    >
      {{ $t("funnel-flow.paid-social.ads.ad-groups.title") }}

      <template #description>
        {{ $t("funnel-flow.paid-social.ads.ad-groups.description") }}
      </template>
    </PageTitle>

    <AdsAssemblyAdGroupCard v-for="adGroup in store.adGroups" :data="adGroup" />
  </FormStepLayout>
</template>
