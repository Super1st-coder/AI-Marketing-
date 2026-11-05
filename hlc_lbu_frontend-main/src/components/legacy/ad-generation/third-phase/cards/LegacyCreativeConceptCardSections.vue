<script setup lang="ts">
interface Props {
  name: string;
  editable?: boolean;
}
defineProps<Props>();
</script>

<template>
  <CardSections>
    <EditableCardSection
      :name="`${name}.concept`"
      title="Concept"
      icon="tabler-box"
      iconVariant="warning"
      :editable="editable"
      :class="{ 'card-concept': !editable }"
    />

    <EditableCardSection
      :name="`${name}.message`"
      title="Message"
      icon="tabler-message-circle"
      iconVariant="success"
      :editable="editable"
      :class="{ 'card-message': !editable }"
    />

    <EditableCardSection
      :name="`${name}.slogan`"
      title="Slogan"
      icon="tabler-quote"
      iconVariant="info"
      :editable="editable"
      :class="{ 'card-slogan': !editable }"
    />
  </CardSections>
</template>
