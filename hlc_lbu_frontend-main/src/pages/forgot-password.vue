<script setup lang="ts">
const { t } = useI18n();

usePageTitle(() => t("routes.forgot-password"));

const { forgotForm, submitEmail } = useForgot();
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
          {{ $t("forgot-password.title") }}
        </h2>
        <img src="/candado.jpg" class="tw:ml-2 tw:h-8" />
      </div>

      <p class="tw:mb-6 tw:text-left tw:text-gray-600">
        {{ $t("forgot-password.paragraph") }}
      </p>

      <form @submit.prevent="submitEmail">
        <div class="tw:mb-4">
          <label
            class="tw:mr-2 tw:mb-2 tw:block tw:text-left tw:text-secondary-text"
            for="email"
          >
            {{ $t("forgot-password.email.label") }}
          </label>
          <input
            type="email"
            id="email"
            data-testid="forgotPasswordInputEmail"
            v-model="forgotForm.email"
            autocomplete="off"
            :placeholder="$t('forgot-password.email.placeholder')"
            class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:outline-hidden tw:focus:border-primary"
          />
        </div>

        <Button
          type="submit"
          data-testid="forgotPasswordSubmitBtn"
          class="tw:w-full"
        >
          {{ $t("forgot-password.submit") }}
        </Button>
      </form>

      <div class="tw:mt-6 tw:mb-4 tw:text-center">
        <router-link
          :to="{ name: 'Login' }"
          class="group tw:inline-flex tw:items-center tw:text-primary"
        >
          <img
            src="/btn-back.jpg"
            class="align-middle tw:mt-2 tw:mr-2 tw:h-6 tw:w-6"
          />
          {{ $t("forgot-password.back-to-login") }}
        </router-link>
      </div>
    </CardBase>
  </AuthLayout>
</template>
