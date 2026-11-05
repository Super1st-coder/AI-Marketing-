<script setup lang="ts">
import type { AdSetSidebar } from "../FunnelPaidSocialFormSideBar.vue";

const props = defineProps<{
  nextSet?: AdSetSidebar;
  selectedAdSet: AdSetSidebar;
}>();

const emit = defineEmits<{
  navigateToAdSet: [adSet: AdSetSidebar];
  goNext: [];
}>();

const isOpen = defineModel<boolean>({ required: true });

const formStore = useFunnelPaidSocialFormStore();
const canProceedToAdsStep = computed(() =>
  formStore.areAllPreviousStepsCompleted("ads"),
);

function handleNavigateToAdSet() {
  if (props.nextSet) {
    emit("navigateToAdSet", props.nextSet);
  }
}

function handleGoNext() {
  emit("goNext");
}
</script>

<template>
  <FunnelPaidSocialFormEndMessageModal v-model="isOpen">
    <template #title>
      {{ $t("funnel-flow.paid-social.creative-angle.end-msg.title") }}
      <br />
      <template v-if="nextSet">
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.end-msg.subtitle.with-next",
            { name: selectedAdSet.name },
          )
        }}
      </template>
      <template v-else>
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.end-msg.subtitle.all-complete",
          )
        }}
      </template>
    </template>

    <template #description>
      <template v-if="nextSet">
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.end-msg.description.with-next",
            { name: nextSet?.name },
          )
        }}
      </template>
      <template v-else>
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.end-msg.description.all-complete",
          )
        }}
      </template>
    </template>

    <template #actions>
      <template v-if="nextSet">
        <Button @click="handleNavigateToAdSet">
          {{
            $t(
              "funnel-flow.paid-social.creative-angle.end-msg.actions.define-creative-angle-for",
              { name: nextSet?.name },
            )
          }}
        </Button>
      </template>
      <template v-else>
        <Alert
          v-if="!canProceedToAdsStep"
          type="warning"
          autoScroll
          class="tw:w-full"
        >
          {{
            $t(
              "funnel-flow.paid-social.creative-angle.end-msg.warning.prerequisite-steps-incomplete",
            )
          }}
        </Alert>
        <Button :disabled="!canProceedToAdsStep" @click="handleGoNext">
          {{ $t("funnel-flow.paid-social.creative-angle.actions.next-step") }}
        </Button>
      </template>

      <Button type="button" variant="text" @click="isOpen = false">
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.end-msg.actions.review-creative-angle",
            { name: selectedAdSet.name },
          )
        }}
      </Button>
    </template>
  </FunnelPaidSocialFormEndMessageModal>
</template>
