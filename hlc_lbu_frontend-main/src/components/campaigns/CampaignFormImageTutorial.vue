<script lang="ts" setup>
const emit = defineEmits<{
  goBack: [];
  goNext: [];
}>();
</script>

<template>
  <FormStepLayout>
    <VideoTutorial>
      <template #chip>
        {{ $t("campaigns.campaignsimage.image.imagetutorial.chip") }}</template
      >
      <template #title>{{
        $t("campaigns.campaignsimage.image.imagetutorial.title")
      }}</template>
      <template #description>
        {{ $t("campaigns.campaignsimage.image.imagetutorial.description") }}
      </template>
      <template #actions>
        <Button type="button" @click="emit('goNext')">
          {{ $t("campaigns.campaignsimage.image.imagetutorial.actionButton") }}
        </Button>
      </template>
    </VideoTutorial>
    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="emit('goBack')" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
