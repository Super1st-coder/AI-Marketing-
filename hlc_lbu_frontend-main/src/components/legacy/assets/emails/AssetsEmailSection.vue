<script setup lang="ts">
interface Props {
  title: string;
  icon?: string;
  headerColor?: string;
  contentBgColor?: string;
}

withDefaults(defineProps<Props>(), {
  icon: "",
  headerColor: "#3b82f6",
  contentBgColor: "#f8fafc",
});
</script>

<template>
  <table style="width: 100%; border-collapse: collapse; margin-bottom: 40px">
    <tbody>
      <tr>
        <td
          :style="`
            background-color: ${headerColor};
            color: white;
            padding: 20px;
            font-size: 20px;
            font-weight: 800;
            text-align: center;
            border-radius: 8px 8px 0 0;
          `"
        >
          {{ icon }} {{ title }}
        </td>
      </tr>
      <tr>
        <td
          :style="`
            padding: 30px;
            background-color: ${contentBgColor};
            border: 1px solid #e5e7eb;
            border-top: none;
            border-radius: 0 0 8px 8px;
          `"
        >
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
