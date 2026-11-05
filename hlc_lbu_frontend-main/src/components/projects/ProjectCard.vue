<script lang="ts" setup>
import { ProyectData } from "@/services/projects/ProjectsApi";
import { RouteLocationRaw, RouterLink } from "vue-router";

const props = defineProps<{ data: ProyectData }>();

const isCompleted = computed(() => props.data.status === "A");

const projectHomeRoute = computed<RouteLocationRaw | undefined>(() =>
  isCompleted
    ? {
        name: "UmbrellaCampaignList",
        params: { projectId: props.data.id },
      }
    : undefined,
);
</script>

<template>
  <CardBase class="tw:p-3">
    <div class="tw:mb-4 tw:flex tw:flex-col tw:gap-2">
      <!-- Product -->
      <component
        :is="isCompleted ? RouterLink : 'div'"
        :to="projectHomeRoute"
        class="tw:flex tw:gap-2"
      >
        <CardDynamicImage
          :src="data?.product?.thumbnail_url ?? undefined"
          class="tw:aspect-square tw:h-[100px] tw:w-[100px] tw:shrink-0"
        />

        <div v-if="data.product" class="tw:min-w-0 tw:grow">
          <h3 class="tw:mb-2 tw:line-clamp-1 tw:text-sm tw:font-bold">
            {{ data.product?.name }}
          </h3>

          <p class="tw:line-clamp-2 tw:text-sm">
            {{ data.product?.description }}
          </p>
        </div>
        <div v-else class="tw:flex tw:flex-col tw:justify-center">
          <p class="tw:text-sm">
            {{ $t("projects.card.no-product-available") }}
          </p>
        </div>
      </component>

      <Separator />

      <!-- Target customer -->
      <component
        :is="isCompleted ? RouterLink : 'div'"
        :to="projectHomeRoute"
        class="tw:flex tw:gap-2"
      >
        <CardDynamicImage
          :src="data?.bperson?.thumbnail_url ?? undefined"
          class="tw:aspect-square tw:h-[100px] tw:w-[100px] tw:shrink-0"
        />

        <div v-if="data.bperson" class="tw:min-w-0 tw:grow">
          <h3 class="tw:mb-2 tw:line-clamp-1 tw:text-sm tw:font-bold">
            {{ data.bperson?.name }}
          </h3>

          <p class="tw:line-clamp-2 tw:text-sm">
            {{ data.bperson?.bperson_story }}
          </p>
        </div>
        <div v-else class="tw:flex tw:flex-col tw:justify-center">
          <p class="tw:text-sm">
            {{ $t("projects.card.no-target-customer-available") }}
          </p>
        </div>
      </component>

      <Separator />
    </div>

    <div class="tw:mb-2.5 tw:flex tw:justify-between">
      <!-- Title -->
      <component :is="isCompleted ? RouterLink : 'div'" :to="projectHomeRoute">
        <h2 class="tw:text-sm tw:font-bold">
          {{ data.name }}
        </h2>
      </component>

      <!-- Dropdown -->
      <ButtonDropdownIcon placement="bottom-start" icon="tabler-dots">
        <template #options>
          <ButtonDropdownOption
            :to="{
              name: 'ProjectSettings',
              params: { projectId: data.id },
            }"
            icon="tabler-pencil"
          >
            {{ $t("global.edit") }}
          </ButtonDropdownOption>
        </template>
      </ButtonDropdownIcon>
    </div>

    <!-- Chips -->
    <ChipList>
      <ChipCompleted :completed="isCompleted" />
    </ChipList>
  </CardBase>
</template>
