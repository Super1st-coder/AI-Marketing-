<script setup lang="ts">
import { useI18n } from "vue-i18n";

const isOpen = defineModel<boolean>({ required: true });
const { t } = useI18n();

const handleStageClick = () => {
  isOpen.value = false;
};

// Keys mapped to icons; labels/descriptions come from i18n
const groups = [
  {
    key: "awareness-channels",
    stages: [
      { key: "blog-post", icon: "tabler-speakerphone", disabled: true },
      { key: "podcast-ad", icon: "tabler-speakerphone", disabled: true },
      { key: "youtube-video", icon: "tabler-speakerphone", disabled: true },
    ],
  },
  {
    key: "lead-generation",
    stages: [
      { key: "webinar-signup", icon: "tabler-speakerphone", disabled: true },
      { key: "quiz-survey", icon: "tabler-speakerphone", disabled: true },
      { key: "ebook-download", icon: "tabler-speakerphone", disabled: true },
    ],
  },
  {
    key: "nurturing-sales",
    stages: [
      { key: "sms-message", icon: "tabler-speakerphone", disabled: true },
      {
        key: "sales-call-booking",
        icon: "tabler-speakerphone",
        disabled: true,
      },
      { key: "ebook-download", icon: "tabler-speakerphone", disabled: true },
    ],
  },
];

const ns = "funnel-flow.home.new-stage-modal";
</script>

<template>
  <Modal v-model="isOpen" class="tw:p-10" :maxWidth="900" closeButton>
    <h2 class="tw:mb-7 tw:text-4xl tw:font-extrabold">
      {{ t(`${ns}.title`) }}
    </h2>

    <div class="tw:grid tw:items-end tw:gap-x-4 tw:gap-y-8 tw:lg:grid-cols-2">
      <FunnelFlowNewFunnelModalGroup v-for="group in groups" :key="group.key">
        <template #title>
          {{ t(`${ns}.groups.${group.key}.title`) }}
        </template>

        <FunnelFlowNewFunnelModalButton
          v-for="stage in group.stages"
          :key="stage.key"
          :name="t(`${ns}.groups.${group.key}.items.${stage.key}.name`)"
          :description="
            t(`${ns}.groups.${group.key}.items.${stage.key}.description`)
          "
          :icon="stage.icon"
          :disabled="stage.disabled"
          @click="handleStageClick"
        />
      </FunnelFlowNewFunnelModalGroup>
    </div>
  </Modal>
</template>
