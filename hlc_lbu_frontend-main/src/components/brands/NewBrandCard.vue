<script lang="ts" setup>
import NewBrandsApi, { BrandData } from "@/services/NewBrandsApi";
import { RouteLocationRaw } from "vue-router";

const props = defineProps<{ data: BrandData }>();

const logos = computed(() =>
  Array.isArray(props.data.logos) ? props.data.logos : props.data.logos.values,
);

// Get the main logo for display
const mainLogo = computed(() =>
  logos.value.find((logo) => logo.category === "main-logo"),
);

const src = computed(() => mainLogo.value?.image_url);

// Delete modal
const router = useRouter();
const isDeleteModalOpen = ref(false);

const handleDelete = async () => {
  await NewBrandsApi.delete(props.data.id);

  // Reload page
  router.go(0);
};

const targetRoute = computed<RouteLocationRaw>(() => ({
  name: props.data.complete ? "Brand" : "BrandSettings",
  params: { brandId: props.data.id },
}));
</script>

<template>
  <CardBase class="tw:p-3">
    <!-- Image -->
    <RouterLink :to="targetRoute">
      <CardDynamicImage
        class="tw:mb-4 tw:aspect-square"
        :src="src"
        fit="contain"
      />
    </RouterLink>

    <div class="tw:mb-2.5 tw:flex tw:justify-between">
      <!-- Title -->
      <RouterLink :to="targetRoute">
        <h2 class="tw:text-sm tw:font-bold">{{ data.name }}</h2>
      </RouterLink>

      <!-- Dropdown -->
      <PermissionGuard
        :requires="[
          { name: 'BRAND', actions: ['U'] },
          { name: 'BRAND', actions: ['D'] },
        ]"
        mode="any"
      >
        <ButtonDropdownIcon placement="bottom-start" icon="tabler-dots">
          <template #options>
            <!-- Edit button -->
            <PermissionGuard :requires="[{ name: 'BRAND', actions: ['U'] }]">
              <ButtonDropdownOption
                :to="{
                  name: 'BrandSettings',
                  params: { brandId: data.id },
                }"
                icon="tabler-pencil"
              >
                {{ $t("global.edit") }}
              </ButtonDropdownOption>
            </PermissionGuard>

            <!-- Delete button -->
            <PermissionGuard :requires="[{ name: 'BRAND', actions: ['D'] }]">
              <ButtonDropdownOption
                icon="tabler-trash"
                @click="isDeleteModalOpen = true"
              >
                {{ $t("global.delete") }}
              </ButtonDropdownOption>
            </PermissionGuard>
          </template>
        </ButtonDropdownIcon>
      </PermissionGuard>
    </div>

    <!-- Chips -->
    <ChipList>
      <ChipCompleted :completed="data.complete" />
    </ChipList>

    <!-- Modal -->
    <ModalDelete v-model="isDeleteModalOpen" :confirmFn="handleDelete">
      <template #title>
        {{ $t("brands.delete-modal.title") }}
      </template>
      <template #description>
        {{ $t("brands.delete-modal.description", { name: data.name }) }}
      </template>
    </ModalDelete>
  </CardBase>
</template>
