<script lang="ts" setup>
defineProps<{ title?: string; name: string }>();
</script>

<template>
  <div>
    <BotSectionSubtitle v-if="title" class="tw:mb-3">
      {{ title }}
    </BotSectionSubtitle>

    <FieldEditableText :name="name" required />
  </div>
</template>
