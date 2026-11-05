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
      :name="`${name}.title`"
      :title="$t('process.target-buyer.card.title')"
      icon="tabler:hexagon-letter-t-filled"
      iconVariant="gray"
      :editable="editable"
      :class="{ 'card-lives': !editable }"
    />

    <EditableCardSection
      :name="`${name}.description`"
      :title="$t('process.target-buyer.card.description')"
      icon="tabler:user-star"
      iconVariant="gray"
      :editable="editable"
      :class="{ 'card-lives': !editable }"
    />

    <EditableCardSection
      :name="`${name}.lives`"
      :title="$t('process.target-buyer.card.lives')"
      icon="tabler-building-skyscraper"
      iconVariant="gray"
      :editable="editable"
      :class="{ 'card-lives': !editable }"
    />

    <EditableCardSection
      :name="`${name}.values`"
      :title="$t('process.target-buyer.card.values')"
      icon="tabler-social"
      iconVariant="info"
      :editable="editable"
      :class="{ 'card-values': !editable }"
    />

    <EditableCardSection
      :name="`${name}.goals`"
      :title="$t('process.target-buyer.card.goals')"
      icon="tabler-pennant"
      iconVariant="warning"
      :editable="editable"
      :class="{ 'card-goals': !editable }"
    />

    <EditableCardSection
      :name="`${name}.needs`"
      :title="$t('process.target-buyer.card.needs')"
      icon="tabler-accessible"
      iconVariant="success"
      :editable="editable"
      :class="{ 'card-needs': !editable }"
    />

    <EditableCardSection
      :name="`${name}.painPoints`"
      :title="$t('process.target-buyer.card.pain-points')"
      icon="tabler-alert-octagon"
      iconVariant="error"
      :editable="editable"
      :class="{ 'card-pain-points': !editable }"
    />
  </CardSections>
</template>
