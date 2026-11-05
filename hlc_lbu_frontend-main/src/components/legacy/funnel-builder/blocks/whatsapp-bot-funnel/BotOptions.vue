<script lang="ts" setup>
import { useField } from "vee-validate";

const props = defineProps<{ name: string }>();

const { value: array, name } = useField<string[]>(() => props.name);
</script>

<template>
  <div>
    <CardTitle
      icon="tabler-git-fork"
      iconVariant="success"
      is="h3"
      class="tw:mb-3"
    >
      Quick Reply Options:
    </CardTitle>

    <div class="tw:flex tw:max-w-[237px] tw:flex-col tw:gap-5">
      <FieldEditableText
        v-for="(_value, index) in array"
        :name="`${name}.${index}`"
        required
        color="dark"
      />
    </div>
  </div>
</template>
