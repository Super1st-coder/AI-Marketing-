<script setup lang="ts">
interface Props {
  label: string;
  value?: string | null;
  isLast?: boolean;
}

withDefaults(defineProps<Props>(), {
  value: null,
  isLast: false,
});
</script>

<template>
  <tr>
    <td
      :style="`
        padding: 15px 0;
        ${!isLast ? 'border-bottom: 1px solid #6b728080;' : ''}
      `"
    >
      <strong
        style="
          color: #374151;
          font-size: 16px;
          display: block;
          margin-bottom: 8px;
        "
        >{{ label }}:</strong
      >
      <span
        style="
          color: #6b7280;
          line-height: 1.6;
          white-space: pre-line;
          font-size: 15px;
        "
        >{{ value || "N/A" }}</span
      >
    </td>
  </tr>
</template>
