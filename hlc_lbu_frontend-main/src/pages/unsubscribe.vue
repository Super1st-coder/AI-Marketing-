<script setup lang="ts">
const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const { unsubscribeAccount } = useRegister();

usePageTitle(() => t("routes.unsubscribe"));

// Access query parameters
const accountEmail = getEmailFromQuery(route.query.account);
const verificationCode = route.query.code ? route.query.code.toString() : "";

onMounted(async () => {
  await unsubscribeAccount(accountEmail, verificationCode);
});

const submitRegisterOk = async () => {
  router.push("/");
};
</script>

<template>
  <AuthLayout>
    <CardBase class="tw:p-6 tw:lg:p-12">
      <div class="tw:mb-4 tw:flex tw:justify-center">
        <img src="/images/logo-hiluca.png" class="tw:h-12" />
      </div>
      <div class="tw:flex tw:items-center">
        <h2
          class="tw:mb-1 tw:text-left tw:text-2xl tw:font-bold tw:text-primary-text"
        >
          {{ t("unsubscribe.title") }}
        </h2>
      </div>
      <p class="tw:mb-6 tw:text-left tw:text-gray-600">
        {{ t("unsubscribe.description") }}
      </p>
      <form @submit.prevent="submitRegisterOk">
        <Button type="submit" class="tw:w-full">
          {{ t("login.submit") }}
        </Button>
      </form>
    </CardBase>
  </AuthLayout>
</template>
