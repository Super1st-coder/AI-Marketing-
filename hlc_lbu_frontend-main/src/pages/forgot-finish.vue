<script setup lang="ts">
import useManagePassword from "@/composables/useManagePassword";
const { t } = useI18n();
usePageTitle(() => t("routes.forgot-finish"));

const { createForm, submitForgotPassword, error, success } =
  useManagePassword();

if (!createForm.value.password) createForm.value.password = "";

const showPassword = ref(false);
const togglePassword = () => (showPassword.value = !showPassword.value);

const passwordRules = {
  minLength: {
    label: t("forgot-password.finish.password-rules.min-length"),
    test: (v: string) => /.{8,}/.test(v),
  },
  uppercase: {
    label: t("forgot-password.finish.password-rules.uppercase"),
    test: (v: string) => /[A-Z]/.test(v),
  },
  number: {
    label: t("forgot-password.finish.password-rules.number"),
    test: (v: string) => /[0-9]/.test(v),
  },
  symbol: {
    label: t("forgot-password.finish.password-rules.symbol"),
    test: (v: string) => /[^A-Za-z0-9]/.test(v),
  },
};

const passwordValidation = computed(() => {
  const pwd = createForm.value.password || "";
  return Object.entries(passwordRules).map(([key, rule]) => ({
    key,
    label: rule.label,
    valid: rule.test(pwd),
  }));
});

const handleSubmit = () => {
  const hasErrors = passwordValidation.value.some((rule) => !rule.valid);
  if (hasErrors) {
    return;
  }
  submitForgotPassword();
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
          class="tw:mb-1 tw:text-left tw:text-3xl tw:font-bold tw:text-primary-text"
        >
          {{ $t("forgot-password.finish.title") }}
          <img
            class="tw:ml-1 tw:inline-block tw:h-8"
            src="/images/emojis/lock.png"
            alt=""
          />
        </h2>
      </div>

      <Alert v-if="error" type="error" class="tw:my-5">
        {{ error }}
      </Alert>

      <Alert v-if="success" type="success" class="tw:my-5">
        {{ success }}
      </Alert>

      <p class="tw:mb-6 tw:text-left tw:text-gray-600">
        {{ $t("forgot-password.finish.description") }}
      </p>

      <form @submit.prevent="handleSubmit">
        <div class="tw:mb-4">
          <label
            class="tw:mb-2 tw:block tw:text-left tw:font-bold"
            for="password"
          >
            {{ $t("forgot-password.finish.password.label") }}
          </label>

          <div class="tw:relative">
            <input
              :type="showPassword ? 'text' : 'password'"
              id="password"
              data-testid="forgotPasswordInputPassword"
              v-model="createForm.password"
              autocomplete="off"
              :placeholder="$t('forgot-password.finish.password.placeholder')"
              class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:pr-10 tw:outline-hidden tw:focus:border-primary"
            />

            <button
              type="button"
              @click="togglePassword"
              class="tw:absolute tw:top-2.5 tw:right-3 tw:text-gray-500 tw:hover:text-gray-700 tw:focus:outline-hidden"
              :aria-label="
                showPassword
                  ? $t('forgot-password.finish.password.hide-password')
                  : $t('forgot-password.finish.password.show-password')
              "
            >
              <Icon
                icon="tabler-eye"
                class="tw:text-2xl"
                v-if="!showPassword"
              />
              <Icon icon="tabler-eye-off" class="tw:text-2xl" v-else />
            </button>
          </div>

          <p class="tw:mt-2 tw:text-sm tw:text-gray-600">
            {{ $t("forgot-password.finish.password.hint") }}
          </p>

          <ul class="tw:mt-2 tw:list-disc tw:pl-5 tw:text-sm">
            <li
              v-for="rule in passwordValidation"
              :key="rule.key"
              :class="rule.valid ? 'tw:text-success' : 'tw:text-error'"
            >
              {{ rule.label }}
            </li>
          </ul>
        </div>

        <Button
          type="submit"
          :disabled="passwordValidation.some((rule) => !rule.valid)"
          data-testid="forgotPasswordSubmitBtn"
          class="tw:w-full"
        >
          {{ $t("forgot-password.finish.submit") }}
        </Button>
      </form>
    </CardBase>
  </AuthLayout>
</template>
