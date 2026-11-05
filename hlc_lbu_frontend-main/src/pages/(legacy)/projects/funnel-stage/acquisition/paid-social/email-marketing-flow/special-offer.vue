<script lang="ts" setup>
import EmailsAPI from "@/services/legacy/EmailsAPI";
</script>

<template>
  <EmailGenericBuilder :api="EmailsAPI.Offer">
    <template #title> Special offer email (last push) </template>
    <template #description>
      This final email provides a special incentive to push them over the line.
    </template>
  </EmailGenericBuilder>
</template>
