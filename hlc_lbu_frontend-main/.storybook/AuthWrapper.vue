<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Icon } from "@iconify/vue";

const PASSWORD = "lucaHiLucaHi2023";

const authorized = ref(false);
const input = ref("");
const showPassword = ref(false);
const errorMessage = ref("");

onMounted(() => {
  const saved = localStorage.getItem("storybook_auth");
  if (saved === PASSWORD) {
    authorized.value = true;
  }
});

function handleSubmit(e: Event) {
  e.preventDefault();
  if (input.value === PASSWORD) {
    localStorage.setItem("storybook_auth", PASSWORD);
    authorized.value = true;
    errorMessage.value = "";
    document.location.reload();
  } else {
    errorMessage.value = "Contraseña incorrecta, intente nuevamente.";
  }
}
</script>

<template>
  <div
    v-if="!authorized"
    class="tw:flex tw:h-screen tw:flex-col tw:items-center tw:justify-center tw:gap-4"
  >
    <h2 class="tw:text-xl">
      Ingrese la contraseña para acceder al Storybook de HiLuca
    </h2>
    <form
      @submit="handleSubmit"
      class="tw:flex tw:flex-col tw:items-center tw:gap-2"
    >
      <div class="tw:relative">
        <input
          v-model="input"
          :type="showPassword ? 'text' : 'password'"
          class="tw:rounded tw:border tw:px-2 tw:py-1 tw:pr-8"
          placeholder="Password"
        />
        <button
          type="button"
          class="tw:absolute tw:top-1/2 tw:right-2 tw:-translate-y-1/2 tw:text-gray-500 tw:hover:text-gray-700"
          @click="showPassword = !showPassword"
        >
          <Icon :icon="showPassword ? 'tabler:eye-off' : 'tabler:eye'" />
        </button>
      </div>

      <button
        type="submit"
        class="tw:rounded tw:bg-primary tw:px-3 tw:py-1 tw:text-white"
      >
        Entrar
      </button>

      <p v-if="errorMessage" class="tw:text-sm tw:text-error">
        {{ errorMessage }}
      </p>
    </form>
  </div>

  <div v-else>
    <slot />
  </div>
</template>
