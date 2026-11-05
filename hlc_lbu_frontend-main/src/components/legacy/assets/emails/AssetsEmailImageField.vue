<script setup lang="ts">
interface Props {
  label: string;
  imageUrl?: string | null;
}

defineProps<Props>();
</script>

<template>
  <tr>
    <td style="padding: 10px 0">
      <strong
        style="
          color: #374151;
          font-size: 16px;
          display: block;
          margin-bottom: 8px;
        "
        >{{ label }}:</strong
      >
      <img
        v-if="imageUrl"
        :src="imageUrl"
        style="
          width: 100%;
          height: auto;
          margin-top: 8px;
          border: 1px solid #e5e7eb;
          border-radius: 4px;
        "
        :alt="`${label} Asset`"
      />
      <span v-else style="color: #6b7280">No image provided</span>
    </td>
  </tr>
</template>
