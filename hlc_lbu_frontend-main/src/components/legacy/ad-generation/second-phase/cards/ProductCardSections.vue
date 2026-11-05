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
      :name="`${name}.advantage`"
      :title="$t('process.product.card.advantage')"
      icon="tabler-chart-arrows-vertical"
      iconVariant="warning"
      :editable="editable"
      :class="{ 'card-advantage': !editable }"
    />

    <EditableCardSection
      :name="`${name}.description`"
      :title="$t('process.product.card.description')"
      icon="tabler-file-text"
      iconVariant="success"
      :editable="editable"
      :class="{ 'card-description': !editable }"
    />

    <EditableCardSection
      :name="`${name}.benefit`"
      :title="$t('process.product.card.benefit')"
      icon="tabler-star"
      iconVariant="info"
      :editable="editable"
      :class="{ 'card-benefit': !editable }"
    />

    <EditableCardSection
      :name="`${name}.details`"
      :title="$t('process.product.card.details')"
      icon="tabler-building"
      iconVariant="gray"
      :editable="editable"
      :class="{ 'card-details': !editable }"
    />
  </CardSections>
</template>
