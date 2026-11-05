<script setup lang="ts">
const store = useFunnelPaidSocialAdsAssemblyStore();
const formStore = useFunnelPaidSocialFormStore();
const { goNext } = useMultiStepFormContext();

const isOpen = defineModel<boolean>({ required: true });

const isLoading = ref(false);
const canProceedToSummary = computed(() =>
  formStore.areAllPreviousStepsCompleted("summary"),
);

const close = () => {
  isOpen.value = false;
  isLoading.value = false;
};

const handleGoToNextAd = async () => {
  if (!store.nextAd) {
    return;
  }

  isLoading.value = true;

  try {
    const isNextAdInAnotherSet = store.nextAdSet?.id !== store.currentSet?.id;

    if (isNextAdInAnotherSet && store.nextAdSet) {
      await store.openAdSet(store.nextAdSet.id);
    } else {
      await store.moveToAd(store.nextAd.id);
      store.setScreen(
        store.isCurrentSetVideoFormat ? store.getVideoResumeScreen() : "refine",
      );
    }

    close();
  } finally {
    isLoading.value = false;
  }
};

const handleGoToSummary = async () => {
  goNext();
};
</script>

<template>
  <FunnelPaidSocialFormEndMessageModal v-model="isOpen">
    <template #title>
      {{ $t("funnel-flow.paid-social.ads.refine.move-forward.title") }}
      <br />
      <template v-if="store.nextAd && store.nextAdSet">
        {{
          $t("funnel-flow.paid-social.ads.refine.move-forward.continue-with", {
            adName: store.nextAd.name,
            adSetName: store.nextAdSet.name,
          })
        }}
      </template>
      <template v-else>
        {{ $t("funnel-flow.paid-social.ads.refine.move-forward.all-complete") }}
      </template>
    </template>

    <template #description>
      <template v-if="store.nextAd">
        {{
          $t("funnel-flow.paid-social.ads.refine.move-forward.description-next")
        }}
      </template>
      <template v-else>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.move-forward.description-summary",
          )
        }}
      </template>
    </template>

    <template #actions>
      <template v-if="store.nextAd && store.nextAdSet">
        <Button @click="handleGoToNextAd" :isLoading="isLoading" type="button">
          {{
            $t("funnel-flow.paid-social.ads.refine.move-forward.button-next", {
              adName: store.nextAd.name,
              adSetName: store.nextAdSet.name,
            })
          }}
        </Button>
      </template>
      <template v-else>
        <Button
          v-if="canProceedToSummary"
          @click="handleGoToSummary"
          :isLoading="isLoading"
          type="button"
        >
          {{
            $t("funnel-flow.paid-social.ads.refine.move-forward.button-summary")
          }}
        </Button>
        <Alert v-else type="warning" autoScroll class="tw:w-full">
          {{
            $t(
              "funnel-flow.paid-social.ads.refine.move-forward.previous-steps-warning",
            )
          }}
        </Alert>
      </template>

      <Button type="button" variant="text" @click="close">
        {{
          $t("funnel-flow.paid-social.ads.refine.move-forward.button-review")
        }}
      </Button>
    </template>
  </FunnelPaidSocialFormEndMessageModal>
</template>
