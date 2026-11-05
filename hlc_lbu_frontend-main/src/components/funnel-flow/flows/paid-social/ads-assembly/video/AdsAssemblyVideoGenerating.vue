<script setup lang="ts">
import { FunnelPaidSocialFormData } from "../../FunnelPaidSocialForm.vue";

// Shown while a step of the video flow generates (scripts, storyboard,
// video). The generation keeps going if the user leaves, so it offers them
// somewhere else to go

defineProps<{
  /** 0-100. Without it, only the spinner shows. */
  percentage?: number;
}>();

const { goToStep, getFlatIndexOfStep } =
  useMultiStepFormContext<FunnelPaidSocialFormData>();

// It replaces a form the user may have scrolled down
onMounted(() => {
  scrollWindowToTop();
});

// A step of the form, not a route, so it's a button
function handleCreateAnotherAd() {
  goToStep(getFlatIndexOfStep({ name: "structure" }), { isDirty: false });
}
</script>

<template>
  <div
    class="tw:flex tw:grow tw:flex-col tw:items-center tw:justify-center tw:px-6 tw:py-12 tw:text-center"
    role="status"
  >
    <!-- The spinner keeps turning: the percentage goes in its center -->
    <div class="tw:relative tw:mb-11 tw:flex tw:items-center tw:justify-center">
      <GradientSpinner />

      <span
        v-if="percentage !== undefined"
        class="tw:absolute tw:text-3xl tw:font-bold tw:text-primary"
      >
        {{ percentage }}%
      </span>
    </div>

    <h2 class="tw:mb-5 tw:text-3xl tw:font-bold">
      <slot name="title" />
    </h2>

    <p
      class="tw:font-medium tw:text-primary"
      :class="$slots.progress ? 'tw:mb-2' : 'tw:mb-7'"
    >
      <slot name="subtitle" />
      <PulsingDots class="tw:ml-1" />
    </p>

    <!-- What's done so far, e.g. "3 of 6 images ready" -->
    <p
      v-if="$slots.progress"
      class="tw:mb-7 tw:text-sm tw:font-medium tw:text-secondary-text"
    >
      <slot name="progress" />
    </p>

    <p
      class="tw:mb-5 tw:text-sm tw:text-secondary-text"
      style="max-width: 314px"
    >
      {{ $t("funnel-flow.paid-social.ads.video.generating.description") }}
    </p>

    <!-- A one-column grid as wide as its widest button, which the others
      stretch to. The centered parent sizes it to its content -->
    <div class="tw:grid tw:gap-5">
      <!-- The campaign's own project, from the current route -->
      <Button
        color="secondary"
        variant="outlined"
        leftIcon="tabler:speakerphone"
        :uppercase="false"
        :to="{ name: 'CampaignList' }"
      >
        {{
          $t(
            "funnel-flow.paid-social.ads.video.generating.view-active-campaigns",
          )
        }}
      </Button>

      <Button
        color="secondary"
        variant="outlined"
        type="button"
        leftIcon="tabler:photo"
        :uppercase="false"
        @click="handleCreateAnotherAd"
      >
        {{
          $t("funnel-flow.paid-social.ads.video.generating.create-another-ad")
        }}
      </Button>

      <Button
        color="secondary"
        variant="outlined"
        leftIcon="tabler:home"
        :uppercase="false"
        :to="{ name: 'Brand' }"
      >
        {{
          $t("funnel-flow.paid-social.ads.video.generating.back-to-dashboard")
        }}
      </Button>
    </div>
  </div>
</template>
