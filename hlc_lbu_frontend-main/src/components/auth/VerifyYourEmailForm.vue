<script setup lang="ts">
import { useRouter } from "vue-router";

const props = defineProps({
  email: {
    type: String,
    required: true,
  },
});
const { resendEmailConfirmation } = useRegister();
const emailResendSucceded = ref<boolean>(false);
const router = useRouter();

const handleSubmit = () => {
  router.push("/");
};

const resendEmail = async () => {
  if (!props.email) {
    return;
  }
  await resendEmailConfirmation(props.email);
  emailResendSucceded.value = true;
  setTimeout(() => {
    emailResendSucceded.value = false;
  }, 3000);
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
          {{ $t("verify-your-email.title") }}
        </h2>
        <img src="/sobre-email.jpg" class="tw:ml-2 tw:h-8" />
      </div>
      <p class="tw:mb-6 tw:text-left tw:text-gray-600">
        {{
          $t("verify-your-email.activation-link-sent", { email: props.email })
        }}
        <br />
        {{ $t("verify-your-email.follow-link-inside") }}<br />
      </p>

      <form @submit.prevent="handleSubmit">
        <Button type="submit" class="tw:w-full">
          {{ $t("verify-your-email.skip-for-now") }}
        </Button>
      </form>
      <div class="tw:mt-6 tw:mb-4 tw:text-center">
        <p class="tw:inline-flex tw:items-center">
          <span class="tw:text-secondary-text">{{
            $t("verify-your-email.didnt-get-the-mail")
          }}</span>
          <a href="#" class="tw:ml-1 tw:text-primary" @click="resendEmail">
            {{ $t("verify-your-email.resend") }}</a
          >
        </p>
        <Alert v-if="emailResendSucceded" type="success" class="tw:self-start">
          {{ $t("verify-your-email.forwarded-email") }}
        </Alert>
      </div>
    </CardBase>
  </AuthLayout>
</template>
