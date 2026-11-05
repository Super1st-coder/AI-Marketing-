<script lang="ts" setup>
import EmailsAPI from "@/services/legacy/EmailsAPI";
</script>

<template>
  <EmailGenericBuilder :api="EmailsAPI.PainPoints">
    <template #title> Address pain points and offer a solution </template>
    <template #description>
      This email should dive into their pain points and remind them how your
      product solves their problems.
    </template>
  </EmailGenericBuilder>
</template>
