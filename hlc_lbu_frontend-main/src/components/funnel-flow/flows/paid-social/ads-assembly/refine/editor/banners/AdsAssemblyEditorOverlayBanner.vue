<script setup lang="ts">
import {
  doesVariantHavePinnedFormat,
  doesVariantHaveValidMedia,
} from "@/services/funnel-flow/paid-social/AdsApi";

const store = useFunnelPaidSocialAdsAssemblyStore();

const currentTab = ref<"copy" | "media">("copy");

const copyAlert = computed(
  () =>
    !doesVariantHaveValidMedia(store.currentVariant) ||
    !doesVariantHavePinnedFormat(store.currentVariant),
);
</script>

<template>
  <Tabs v-model="currentTab" size="lg" class="tw:flex tw:grow tw:flex-col">
    <Container :maxWidth="1088">
      <TabsList>
        <Tab value="copy" :hasAlert="copyAlert">
          {{
            $t("funnel-flow.paid-social.ads.refine.editor.banner.tabs.copy-in")
          }}
        </Tab>

        <Tab value="media">
          {{
            $t(
              "funnel-flow.paid-social.ads.refine.editor.banner.tabs.image-video",
            )
          }}
        </Tab>
      </TabsList>
    </Container>

    <TabPanel value="copy" class="tw:flex tw:grow tw:flex-col">
      <AdsAssemblyEditorOverlayBannerCopy />
    </TabPanel>

    <TabPanel value="media" useSuspense class="tw:flex tw:grow tw:flex-col">
      <AdsAssemblyEditorOverlayBannerMedia />
    </TabPanel>
  </Tabs>
</template>
