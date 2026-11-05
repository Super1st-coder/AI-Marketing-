<script lang="ts" setup>
import { RouteLocationNormalizedGeneric } from "vue-router";
import { setLocale } from "yup";

const { locale, t } = useI18n();
const authStore = useAuthStore();

onMounted(() => {
  authStore.initSessionWatchdog();
});

watch(
  locale,
  () => {
    setLocale({
      mixed: {
        required: t("forms.field-required"),
      },
      string: {
        url: t("forms.url-invalid"),
        email: t("forms.email-invalid"),
      },
    });
  },
  { immediate: true },
);

const getKey = (route: RouteLocationNormalizedGeneric) => {
  if (route.meta.key) {
    const key = route.meta.key;

    if (typeof key === "string") {
      return key;
    }

    return key(route);
  }

  // Get the parameters
  const params = { ...route.params };

  // Remove locale
  if ("locale" in params) {
    delete params.locale;
  }

  return Object.values(params).join();
};
</script>

<template>
  <v-app>
    <NotificationHost />

    <v-main>
      <RouterView v-slot="{ Component, route }">
        <template v-if="Component">
          <ErrorBoundary :key="getKey(route)">
            <Suspense timeout="0">
              <component :is="Component"></component>

              <template #fallback>
                <LoadingScreen />
              </template>
            </Suspense>

            <template #fallback="{ error }">
              <ErrorScreen :error="error" useDefaultAction />
            </template>
          </ErrorBoundary>
        </template>
      </RouterView>
    </v-main>
  </v-app>
</template>
