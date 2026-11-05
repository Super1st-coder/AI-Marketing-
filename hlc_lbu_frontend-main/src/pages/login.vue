<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { boolean, object, string } from "yup";
import { AUTH_SESSION_EXPIRED_QUERY_KEY } from "@/constants/auth";

const { t } = useI18n();
usePageTitle(() => t("routes.login"));

const authStore = useAuthStore();
const route = useRoute();

const showPassword = ref(false);

onMounted(() => {
  if (!isSessionExpiredQuery(route.query?.[AUTH_SESSION_EXPIRED_QUERY_KEY])) {
    return;
  }

  useNotificationStore().display({
    type: "info",
    title: t("auth.session-expired.title"),
    description: t("auth.session-expired.description"),
    durationMs: null,
  });

  // Remove the session expired query parameter
  // const { [AUTH_SESSION_EXPIRED_QUERY_KEY]: _, ...restQuery } = route.query;
  // router.replace({ ...route, query: restQuery });
});

const schema = toTypedSchema(
  object().shape({
    email: string().required(),
    password: string().required(),
    rememberMe: boolean().optional(),
  }),
);

const generalErrorMessage = ref<string | undefined>();
const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
});

const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;

  try {
    await authStore.login({ email: values.email, password: values.password });
    await sleep(1000);
  } catch (error) {
    generalErrorMessage.value = t("login.errors.verify-your-credentials");
  }
});
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
          {{ $t("login.title") }}
        </h2>
        <img src="/mano-saluda.jpg" class="tw:ml-2 tw:h-8" />
      </div>
      <p class="tw:mb-8 tw:text-left tw:text-gray-600">
        {{ $t("login.paragraph") }}
      </p>

      <form @submit.prevent="onSubmit">
        <FieldsContainer>
          <FieldText
            name="email"
            :label="$t('login.email.label')"
            :placeholder="$t('login.email.placeholder')"
            autocomplete="username"
            data-testid="username"
          />

          <FieldText
            name="password"
            :type="showPassword ? 'text' : 'password'"
            :label="$t('login.password.label')"
            :placeholder="$t('login.password.placeholder')"
            autocomplete="current-password"
            data-testid="password"
            :rightIcon="showPassword ? 'tabler:eye' : 'tabler:eye-off'"
            rightIconClickable
            @clickRightIcon="showPassword = !showPassword"
          />

          <div class="tw:flex tw:items-center tw:justify-between">
            <FieldCheckbox
              name="rememberMe"
              :label="$t('login.remember-me')"
              data-testid="rememberMe"
            />

            <RouterLink
              :to="{ name: 'ForgotPassword' }"
              class="tw:text-primary"
              data-testid="forgotPasswordLink"
            >
              {{ $t("login.forgot-password") }}
            </RouterLink>
          </div>

          <Alert v-if="generalErrorMessage" type="error" autoScroll>
            {{ generalErrorMessage }}
          </Alert>

          <Button type="submit" :isLoading="isSubmitting">
            {{ $t("login.submit") }}
          </Button>
        </FieldsContainer>
      </form>

      <!-- Link to register, removed temporally -->
      <!-- <div class="tw:mb-8 tw:mt-6 tw:text-center">
        <p class="tw:inline-flex tw:items-center">
          <span class="tw:text-secondary-text">
            <i18n-t keypath="login.new-on-our-platform">
              <template #action>
                <router-link
                  :to="{ name: 'Register' }"
                  data-testid="createAccountLink"
                  class="tw:ml-1 tw:text-primary"
                >
                  {{ $t("login.create-an-account") }}
                </router-link>
              </template>
            </i18n-t>
          </span>
        </p>
      </div> -->
    </CardBase>
  </AuthLayout>
</template>

<style scoped>
.check {
  width: 20px;
  height: 20px;
  cursor: pointer;

  /* El siguiente selector se aplica cuando el checkbox está seleccionado */
  &:checked {
    background-color: orange;
    border-color: orange;
  }
}
</style>
