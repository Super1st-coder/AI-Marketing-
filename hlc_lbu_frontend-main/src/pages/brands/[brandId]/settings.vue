<script setup lang="ts">
const route = useRoute();
const brandId = useBrandId();
const { t } = useI18n();

// Fetch brand data
const store = useBrandFormStore();
await store.initialize(brandId);

usePageTitle(() => t("routes.settings", { brand: store.brand?.name ?? "" }));

const currentTab = ref<
  "overview" | "identity" | "logos" | "colors" | "typography" | "dosAndDonts"
>("overview");

const tabs = computed(() => [
  {
    value: "identity" as const,
    label: t("brands.settings.tabs.identity"),
    icon: "custom:summary",
    isCompleted: store.isIdentityCompleted,
    tooltipText: t("brands.settings.tabs.identity-tooltip"),
  },
  {
    value: "logos" as const,
    label: t("brands.settings.tabs.logos"),
    icon: "custom:logo",
    isCompleted: store.areLogosCompleted,
    tooltipText: t("brands.settings.tabs.logos-tooltip"),
  },
  {
    value: "colors" as const,
    label: t("brands.settings.tabs.colors"),
    icon: "custom:color-palette",
    isCompleted: store.areColorsCompleted,
    tooltipText: t("brands.settings.tabs.colors-tooltip"),
  },
  {
    value: "typography" as const,
    label: t("brands.settings.tabs.typography"),
    icon: "custom:typography",
    isCompleted: store.areTypographiesCompleted,
    tooltipText: t("brands.settings.tabs.typography-tooltip"),
  },
  {
    value: "dosAndDonts" as const,
    label: t("brands.settings.tabs.dos-and-donts"),
    icon: "custom:arrow-split",
    isCompleted: true,
  },
]);

const successModalVariant = computed<undefined | "manual" | "extracted">(() =>
  route.query.justCreated === "manual"
    ? "manual"
    : route.query.justCreated === "extracted"
      ? "extracted"
      : undefined,
);
const showSuccessModal = ref(successModalVariant.value !== undefined);
const showEditModal = ref(false);

// Display modal when the brand is completed
const showCompletedModal = ref(false);
watch(
  () => store.isCompleted,
  (isCompleted) => {
    if (isCompleted) {
      showCompletedModal.value = true;
    }
  },
);

onUnmounted(() => {
  store.free();
});
</script>

<template>
  <Tabs v-model="currentTab" size="lg">
    <GenericSubLayout belowNavbar>
      <template #headerBackAction>
        <RouterLink :to="{ name: 'BrandList' }">
          <Icon icon="tabler-arrow-left" class="tw:text-2xl" />
        </RouterLink>
      </template>

      <template #headerLeft>
        <h2 class="tw:pl-3 tw:font-medium">
          {{ store.brand.name }}
        </h2>

        <button>
          <Icon
            icon="tabler:pencil"
            class="tw:text-2xl tw:text-gray-400"
            @click="showEditModal = true"
          />
        </button>
      </template>

      <template #headerRight>
        <TabsList>
          <Tab value="overview" icon="custom:summary">
            {{ $t("brands.settings.tabs.overview") }}
          </Tab>

          <Tooltip
            v-for="tab in tabs"
            :disabled="tab.isCompleted || !tab.tooltipText"
            placement="bottom"
            :maxWidth="200"
          >
            <Tab
              :value="tab.value"
              :icon="tab.icon"
              :hasAlert="!tab.isCompleted"
            >
              {{ tab.label }}
            </Tab>

            <template #content>
              {{ tab.tooltipText }}
            </template>
          </Tooltip>
        </TabsList>
      </template>

      <TabPanel value="overview" useSuspense>
        <BrandFormTabOverview />
      </TabPanel>

      <TabPanel value="identity" useSuspense>
        <BrandFormTabIdentity />
      </TabPanel>

      <TabPanel value="logos" useSuspense>
        <BrandFormTabLogos />
      </TabPanel>

      <TabPanel value="colors" useSuspense>
        <BrandFormTabColors />
      </TabPanel>

      <TabPanel value="typography" useSuspense>
        <BrandFormTabTypography />
      </TabPanel>

      <TabPanel value="dosAndDonts" useSuspense>
        <BrandFormTabDosAndDonts />
      </TabPanel>
    </GenericSubLayout>

    <!-- Modal to display when the brand was just created -->
    <BrandSettingsSuccessModal
      v-if="showSuccessModal && successModalVariant"
      v-model="showSuccessModal"
      :variant="successModalVariant"
    />

    <!-- Modal to display when the brand is edited-->
    <BrandFormEditModal v-if="showEditModal" v-model="showEditModal" />

    <!-- Modal to display when the brand is completed -->
    <BrandSettingsCompletedModal
      v-if="showCompletedModal"
      v-model="showCompletedModal"
    />
  </Tabs>
</template>
