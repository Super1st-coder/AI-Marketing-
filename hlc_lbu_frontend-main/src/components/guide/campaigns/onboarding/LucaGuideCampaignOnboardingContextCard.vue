<script setup lang="ts">
import { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import type { RouteLocationRaw } from "vue-router";

defineProps<{
  name: string;
  title: string;
  description: string;
  options: AutocompleteOption[];
  searchPlaceholder: string;
  loading?: boolean;
  createTo?: RouteLocationRaw;
}>();

const emit = defineEmits<{
  create: [];
}>();

function handleCreate() {
  emit("create");
}
</script>

<template>
  <CardBase borderRadius="lg" class="tw:p-6">
    <h3 class="tw:mb-1 tw:text-base tw:font-bold tw:text-primary-text">
      {{ title }}
    </h3>

    <p class="tw:mb-5 tw:text-sm tw:text-secondary-text">
      {{ description }}
    </p>

    <FieldAutocomplete
      :name="name"
      :options="options"
      leftIcon="tabler:search"
      :placeholder="searchPlaceholder"
      clearable
      :loading="loading"
    >
      <template #buttons>
        <Link
          v-if="createTo"
          :to="createTo"
          class="tw:shrink-0 tw:self-center tw:text-sm tw:font-medium tw:whitespace-nowrap"
        >
          {{ $t("luca-guide.campaigns.onboarding.context.create-new") }}
        </Link>
        <Link
          v-else
          is="button"
          class="tw:shrink-0 tw:self-center tw:text-sm tw:font-medium tw:whitespace-nowrap"
          @click="handleCreate"
        >
          {{ $t("luca-guide.campaigns.onboarding.context.create-new") }}
        </Link>
      </template>
    </FieldAutocomplete>
  </CardBase>
</template>
