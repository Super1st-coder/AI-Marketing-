<script setup lang="ts">
const { t } = useI18n();
usePageTitle(() => t("routes.register"));

const showRegistercomp = ref(true);
const email = ref("");

const updateShowRegistercomp = (newValue: boolean) => {
  showRegistercomp.value = newValue;
};
const updateEmailstate = (newEmail: string) => {
  email.value = newEmail;
};
</script>

<template>
  <RegisterForm
    v-if="showRegistercomp"
    :showRegistercomp="showRegistercomp"
    :updateShowRegistercomp="updateShowRegistercomp"
    :email="email"
    @update:email="email = $event"
    :updateEmailstate="updateEmailstate"
  />
  <VerifyYourEmailForm :email="email" v-else />
</template>
