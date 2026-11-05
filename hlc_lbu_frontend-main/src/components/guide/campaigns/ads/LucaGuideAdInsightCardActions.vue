<script setup lang="ts">
const emit = defineEmits<{
  viewInsight: [];
}>();
</script>

<template>
  <div class="tw:mt-auto tw:flex tw:items-center tw:justify-between tw:gap-2">
    <div></div>
    <!-- TODO: Add add to plan button -->
    <!-- <Button type="button" size="sm" leftIcon="tabler:clipboard-plus">
        {{ $t("luca-guide.ads.detail.diagnosis.add-to-plan") }}
      </Button> -->

    <div class="gap tw:flex tw:gap-3">
      <!-- View insight button -->
      <Button
        type="button"
        size="sm"
        variant="outlined"
        color="secondary"
        @click="emit('viewInsight')"
      >
        {{ $t("luca-guide.ads.detail.diagnosis.view-insight") }}
      </Button>

      <!-- Delete button -->
      <Button
        type="button"
        size="sm"
        square
        variant="outlined"
        color="secondary"
        icon="tabler:trash"
        :aria-label="$t('luca-guide.ads.detail.diagnosis.delete')"
      />
    </div>
  </div>
</template>
