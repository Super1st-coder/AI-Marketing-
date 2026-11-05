<script setup lang="ts">
defineProps<{
  icon: string;
  label: string;
  color: "success" | "info" | "warning" | "error";
  percent: string;
  spend: string;
  adsCount: number;
}>();
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-2 tw:p-4">
    <div
      class="tw:flex tw:items-center tw:gap-2 tw:font-semibold"
      :class="{
        'tw:text-success': color === 'success',
        'tw:text-info': color === 'info',
        'tw:text-warning': color === 'warning',
        'tw:text-error': color === 'error',
      }"
    >
      <Icon :icon="icon" class="tw:text-[20px]" />
      {{ label }}
    </div>

    <p class="tw:text-sm tw:leading-tight">
      <span class="tw:text-xl tw:font-bold">{{ percent }}</span>

      <span class="tw:ml-1 tw:text-secondary-text">
        {{
          $t("luca-guide.campaigns.spend.spend-ads", {
            spend,
            count: adsCount,
          })
        }}
      </span>
    </p>
  </div>
</template>
