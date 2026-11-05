<script lang="ts" setup>
import EmailsAPI from "@/services/legacy/EmailsAPI";
</script>

<template>
  <EmailGenericBuilder :api="EmailsAPI.Urgency">
    <template #title> Urgency / Scarcity Email </template>
    <template #description>
      This email introduces urgency to encourage immediate action.
    </template>
  </EmailGenericBuilder>
</template>
