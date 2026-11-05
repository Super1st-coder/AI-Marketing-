<script setup lang="ts">
import {
  doesVariantHavePinnedFormat,
  doesVariantHaveValidAttributes,
  doesVariantHaveValidMedia,
} from "@/services/funnel-flow/paid-social/AdsApi";

const store = useFunnelPaidSocialAdsAssemblyStore();

const isOpen = defineModel<boolean>({ required: true });

// Video ads have no banner. They edit their segments (the clips of the video)
// and the captions instead
const isVideo = computed(() => store.isCurrentSetVideoFormat);

const currentTab = ref<"banner" | "segments" | "captions">(
  isVideo.value ? "segments" : "banner",
);

async function handleClose() {
  // Save locking
  if ((await useSaveLockingStore().execute()) === "cancel") return;

  isOpen.value = false;
}

const editBannerAlert = computed(
  () =>
    !doesVariantHaveValidMedia(store.currentVariant) ||
    !doesVariantHavePinnedFormat(store.currentVariant),
);

const captionsAlert = computed(
  () => !doesVariantHaveValidAttributes(store.currentVariant),
);

const tutorialModal = useTemplateRef("tutorialModal");
</script>

<template>
  <FullScreenOverlay v-model="isOpen" mode="navbar">
    <Tabs v-model="currentTab" variant="buttonGroup" size="lg">
      <GenericSubLayout>
        <template #headerBackAction>
          <button type="button" @click="handleClose">
            <Icon icon="tabler-arrow-left" class="tw:text-2xl" />
          </button>
        </template>

        <template #headerLeft>
          <h2>
            <span class="tw:line-clamp-1 tw:font-medium">
              {{
                $t("funnel-flow.paid-social.ads.refine.editor.editing", {
                  adName: store.currentAd?.ad_name,
                })
              }}
              <br />
            </span>

            <span class="tw:text-sm tw:text-secondary-text">
              {{
                $t("funnel-flow.paid-social.ads.refine.editor.ad-id", {
                  adId: store.currentAd?.ad_id,
                })
              }}
            </span>
          </h2>
        </template>

        <template #headerCenter>
          <TabsList>
            <Tab
              v-if="!isVideo"
              value="banner"
              icon="tabler:photo"
              :hasAlert="editBannerAlert"
            >
              {{
                $t("funnel-flow.paid-social.ads.refine.editor.tabs.edit-banner")
              }}
            </Tab>

            <Tab v-if="isVideo" value="segments" icon="tabler:photo">
              {{
                $t("funnel-flow.paid-social.ads.refine.editor.tabs.segments")
              }}
            </Tab>

            <Tab
              value="captions"
              icon="tabler:text-resize"
              :hasAlert="captionsAlert"
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.editor.tabs.edit-captions",
                )
              }}
            </Tab>
          </TabsList>
        </template>

        <template #headerRight>
          <HelpButton size="sm" @click="tutorialModal?.open()" />
        </template>

        <!-- The panels grow to the bottom of the screen, so a tab with little
          content still has its footer at the bottom -->
        <template #custom>
          <GradientBackground class="tw:flex tw:grow tw:flex-col">
            <TabPanel
              v-if="!isVideo"
              value="banner"
              class="tw:flex tw:grow tw:flex-col"
            >
              <AdsAssemblyEditorOverlayBanner />
            </TabPanel>

            <!-- Loads the model and voice names before showing -->
            <TabPanel
              v-if="isVideo"
              value="segments"
              useSuspense
              class="tw:flex tw:grow tw:flex-col"
            >
              <AdsAssemblyEditorOverlaySegments @exit="isOpen = false" />
            </TabPanel>

            <TabPanel value="captions" class="tw:flex tw:grow tw:flex-col">
              <AdsAssemblyEditorOverlayCaptions />
            </TabPanel>
          </GradientBackground>
        </template>
      </GenericSubLayout>
    </Tabs>

    <AdsAssemblyEditorOverlayTutorialModal ref="tutorialModal" />
  </FullScreenOverlay>
</template>
