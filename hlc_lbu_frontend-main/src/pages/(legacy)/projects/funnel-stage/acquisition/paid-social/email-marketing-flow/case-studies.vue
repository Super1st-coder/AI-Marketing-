<script lang="ts" setup>
import EmailsAPI from "@/services/legacy/EmailsAPI";
</script>

<template>
  <EmailGenericBuilder :api="EmailsAPI.UseCase">
    <template #title> Social proof / Case studies </template>
    <template #description>
      This email uses trust signals like testimonials or case studies to show
      real-world results.
    </template>
  </EmailGenericBuilder>
</template>
