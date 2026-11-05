<script setup lang="ts">
import useManagePassword from "@/composables/useManagePassword";
const { t } = useI18n();
usePageTitle(() => t("routes.signup-finish"));

const { createForm, submitCreatePassword, error, success } =
  useManagePassword();

if (!createForm.value.password) createForm.value.password = "";

const showPassword = ref(false);
const togglePassword = () => (showPassword.value = !showPassword.value);

const passwordRules = {
  minLength: {
    label: t("signup-finish.password-rules.min-length"),
    test: (v: string) => /.{8,}/.test(v),
  },
  uppercase: {
    label: t("signup-finish.password-rules.uppercase"),
    test: (v: string) => /[A-Z]/.test(v),
  },
  number: {
    label: t("signup-finish.password-rules.number"),
    test: (v: string) => /[0-9]/.test(v),
  },
  symbol: {
    label: t("signup-finish.password-rules.symbol"),
    test: (v: string) => /[^A-Za-z0-9]/.test(v),
  },
};

const passwordValidation = computed(() => {
  const pwd = createForm.value.password || "";
  const confirmPwd = createForm.value.confirmPassword || "";

  const baseRules = Object.entries(passwordRules).map(([key, rule]) => ({
    key,
    label: rule.label,
    valid: rule.test(pwd),
  }));

  if (confirmPwd.length > 0) {
    baseRules.push({
      key: "match",
      label: t("signup-finish.password-rules.match"),
      valid: pwd === confirmPwd,
    });
  }

  return baseRules;
});

const handleSubmit = async () => {
  const hasErrors = passwordValidation.value.some((rule) => !rule.valid);
  if (hasErrors) return;

  await submitCreatePassword();
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
          {{ $t("signup-finish.title") }}
          <img
            class="tw:ml-1 tw:inline-block tw:h-8"
            src="/images/emojis/key.png"
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
        {{ $t("signup-finish.description") }}
      </p>

      <form @submit.prevent="handleSubmit">
        <div class="tw:mb-4">
          <label
            class="tw:mb-2 tw:block tw:text-left tw:font-bold"
            for="password"
          >
            {{ $t("signup-finish.password.label") }}
          </label>

          <div class="tw:relative">
            <input
              :type="showPassword ? 'text' : 'password'"
              id="password"
              data-testid="forgotPasswordInputPassword"
              v-model="createForm.password"
              autocomplete="off"
              :placeholder="$t('signup-finish.password.placeholder')"
              class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:pr-10 tw:outline-hidden tw:focus:border-primary"
            />

            <button
              type="button"
              @click="togglePassword"
              class="tw:absolute tw:top-2.5 tw:right-3 tw:text-gray-500 tw:hover:text-gray-700 tw:focus:outline-hidden"
              :aria-label="
                showPassword
                  ? $t('signup-finish.password.hide-password')
                  : $t('signup-finish.password.show-password')
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
            {{ $t("signup-finish.password.hint") }}
          </p>

          <ul class="tw:mt-2 tw:list-disc tw:pl-5 tw:text-sm">
            <li
              v-for="rule in passwordValidation.filter(
                (rule) => rule.key !== 'match',
              )"
              :key="rule.key"
              :class="rule.valid ? 'tw:text-success' : 'tw:text-error'"
            >
              {{ rule.label }}
            </li>
          </ul>

          <div class="tw:relative tw:mt-4">
            <label
              class="tw:mb-2 tw:block tw:text-left tw:font-bold"
              for="password"
            >
              {{ $t("signup-finish.confirm-password.label") }}
            </label>

            <input
              :type="showPassword ? 'text' : 'password'"
              id="password"
              data-testid="forgotPasswordInputPassword"
              v-model="createForm.confirmPassword"
              autocomplete="off"
              :placeholder="$t('signup-finish.confirm-password.placeholder')"
              class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:pr-10 tw:outline-hidden tw:focus:border-primary"
            />

            <button
              type="button"
              @click="togglePassword"
              class="tw:absolute tw:top-2.5 tw:right-3 tw:text-gray-500 tw:hover:text-gray-700 tw:focus:outline-hidden"
              :aria-label="
                showPassword
                  ? $t('signup-finish.password.hide-password')
                  : $t('signup-finish.password.show-password')
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

          <ul class="tw:list-disc tw:pl-5">
            <li
              v-if="
                passwordValidation.find((r) => r.key === 'match' && !r.valid)
              "
              class="tw:mt-2 tw:text-sm tw:text-error"
            >
              {{ $t("signup-finish.password-rules.match") }}
            </li>
          </ul>
        </div>

        <Button
          type="submit"
          :disabled="passwordValidation.some((rule) => !rule.valid)"
          data-testid="forgotPasswordSubmitBtn"
          class="tw:w-full"
        >
          {{ $t("signup-finish.submit") }}
        </Button>
      </form>
    </CardBase>
  </AuthLayout>
</template>
