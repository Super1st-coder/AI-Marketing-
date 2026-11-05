<script setup lang="ts">
interface Props {
  title: string;
}

defineProps<Props>();
</script>

<template>
  <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px">
    <tbody>
      <tr>
        <td style="padding: 24px 0 10px 0">
          <span style="font-size: 22px; font-weight: 800; color: #1f2937">
            {{ title }}
          </span>
        </td>
      </tr>
      <tr>
        <td style="padding: 0">
          <table style="width: 100%; border-collapse: collapse">
            <tbody>
              <slot></slot>
            </tbody>
          </table>
        </td>
      </tr>
    </tbody>
  </table>
</template>
