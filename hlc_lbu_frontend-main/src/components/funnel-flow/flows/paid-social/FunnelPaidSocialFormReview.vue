<script setup lang="ts">
const { goNext } = useMultiStepFormContext();
</script>

<template>
  <FormStepLayout>
    <VideoTutorial>
      <template #chip>{{
        $t("funnel-flow.paid-social.form-review.video.chip")
      }}</template>
      <template #title>{{
        $t("funnel-flow.paid-social.form-review.video.title")
      }}</template>
      <template #description>{{
        $t("funnel-flow.paid-social.form-review.video.description")
      }}</template>
      <template #actions>
        <Button @click="goNext">
          {{
            $t(
              "funnel-flow.paid-social.form-review.video.actions.confirm-approve",
            )
          }}
        </Button>
      </template>
    </VideoTutorial>
  </FormStepLayout>
</template>
