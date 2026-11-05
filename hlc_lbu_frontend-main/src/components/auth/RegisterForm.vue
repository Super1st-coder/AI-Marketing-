<script setup lang="ts">
const emit = defineEmits(["update:showRegistercomp", "update:email"]);

const props = defineProps({
  showRegistercomp: {
    type: Boolean,
    default: true,
  },
  updateShowRegistercomp: {
    type: Function,
    required: true,
  },
  email: {
    type: String,
    required: true,
  },
  updateEmailstate: {
    type: Function,
    required: true,
  },
});

const { registerForm, submitRegister, errors, isValid } = useRegister();

const submitRegisterOk = async () => {
  const status: number = await submitRegister();
  if (status == 1) {
    props.updateShowRegistercomp(false);
    props.updateEmailstate(registerForm.value.email);
  }
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
          {{ $t("register.title") }}
        </h2>
        <!-- <img src="/rocket.jpg" class="tw:ml-2 tw:h-8" /> -->
      </div>

      <p class="tw:mb-6 tw:text-left tw:text-gray-600">
        {{ $t("register.paragraph") }}
      </p>

      <form @submit.prevent="submitRegisterOk" data-testid="createAccountForm">
        <div
          v-if="errors.trim().length > 0"
          class="tw:bg-red-100 tw:border-red-400 tw:text-red-700 tw:rounded-md tw:border tw:px-4 tw:py-3"
          role="alert"
          data-testid="createAccountError"
        >
          <strong class="tw:font-bold">{{ $t("register.error-title") }}</strong>
          <span class="sm:inline tw:block"> {{ errors }} </span>
        </div>

        <div class="tw:mb-4">
          <label
            class="tw:mr-2 tw:mb-2 tw:block tw:text-left tw:text-secondary-text"
            for="nombres"
          >
            {{ $t("register.names.label") }}
          </label>
          <input
            type="text"
            id="nombres"
            data-testid="createAccountNames"
            autocomplete="off"
            v-model="registerForm.nombres"
            :placeholder="$t('register.names.placeholder')"
            class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:outline-hidden tw:focus:border-primary"
          />
        </div>
        <div class="tw:mb-4">
          <label
            class="tw:mb-2 tw:block tw:text-left tw:text-secondary-text"
            for="apellido"
          >
            {{ $t("register.last-names.label") }}
          </label>
          <input
            type="text"
            id="apellido"
            data-testid="createAccountLastNames"
            v-model="registerForm.apellidos"
            autocomplete="off"
            class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:outline-hidden tw:focus:border-primary"
          />
        </div>
        <div class="tw:mb-4">
          <label
            class="tw:mr-2 tw:mb-2 tw:block tw:text-left tw:text-secondary-text"
            for="email"
          >
            {{ $t("register.email.label") }}
          </label>
          <input
            type="email"
            id="email"
            data-testid="createAccountEmail"
            v-model="registerForm.email"
            autocomplete="off"
            :placeholder="$t('register.email.placeholder')"
            class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:outline-hidden tw:focus:border-primary"
          />
        </div>
        <div class="tw:mb-4">
          <label
            class="tw:mr-2 tw:mb-2 tw:block tw:text-left tw:text-secondary-text"
            for="password"
          >
            {{ $t("register.password.label") }}
          </label>
          <input
            type="password"
            id="password"
            data-testid="createAccountPassword"
            v-model="registerForm.password"
            :placeholder="$t('register.password.placeholder')"
            autocomplete="off"
            minlength="8"
            aria-describedby="password-hint"
            class="tw:w-full tw:rounded tw:border tw:border-input-border tw:px-3 tw:py-2 tw:outline-hidden tw:focus:border-primary"
          />

          <p
            id="password-hint"
            class="tw:mt-1 tw:text-xs tw:text-gray-500"
            aria-live="polite"
          >
            {{ $t("register.password.hint") }}
          </p>
        </div>
        <div class="tw:mt-6 tw:mb-4 tw:text-center">
          <p class="tw:inline-flex tw:items-center">
            <input
              type="checkbox"
              v-model="registerForm.aceptaTerminos"
              checked
              class="check tw:mr-2 tw:bg-primary"
              data-testid="createAccountTerms"
            />
            <span class="tw:text-secondary-text">
              <i18n-t keypath="register.i-agree-to">
                <template #action>
                  <a
                    href="/Terms And Conditions.pdf"
                    target="_blank"
                    class="tw:ml-1 tw:text-primary"
                  >
                    {{ $t("register.privacy-policy-and-terms") }}
                  </a>
                </template>
              </i18n-t>
            </span>
          </p>
        </div>

        <Button
          type="submit"
          class="tw:w-full"
          :disabled="!isValid"
          data-testid="createAccountSubmit"
        >
          {{ $t("register.submit") }}
        </Button>

        <div class="tw:mt-4 tw:text-center">
          <router-link
            :to="{ name: 'Login' }"
            class="tw:cursor-pointer tw:text-sm tw:text-secondary-text tw:hover:text-primary"
          >
            <i18n-t keypath="register.already-have-account" tag="span">
              <template #action>
                <!-- Mantenemos el estilo específico para "Log in", pero ya no es un link separado -->
                <span class="tw:font-medium tw:text-primary">
                  {{ $t("register.log-in") }}
                </span>
              </template>
            </i18n-t>
          </router-link>
        </div>
      </form>
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
