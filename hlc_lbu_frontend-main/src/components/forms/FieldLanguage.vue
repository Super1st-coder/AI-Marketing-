<script lang="ts" setup>
import { appLocalesArray } from "@/plugins/i18n";
import type { FieldBaseNewSelectProps } from "./base/FieldBaseNewSelect.vue";

interface Props extends Omit<FieldBaseNewSelectProps, "options"> {
  name: string;
}

const props = defineProps<Props>();
</script>

<template>
  <FieldNewSelect
    v-bind="props"
    :options="
      appLocalesArray.map((locale) => ({
        value: locale.apiName,
        label: locale.name,
      }))
    "
  >
    <template v-for="(_, name) in $slots" #[name]="scope">
      <slot :name v-bind="scope ?? {}" />
    </template>
  </FieldNewSelect>
</template>
