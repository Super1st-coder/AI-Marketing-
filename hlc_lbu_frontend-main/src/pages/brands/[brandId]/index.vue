<script lang="ts" setup>
const store = useBrandLayoutStore();
const { t } = useI18n();
usePageTitle(() => t("routes.brand", { brand: store.brand?.name ?? "" }));

const showCreateNewAssetModal = ref(false);

const currentTab = ref("create");
</script>

<template>
  <Tabs v-model="currentTab">
    <template #list>
      <Tab value="create" icon="tabler-plus"> {{ $t("global.create") }} </Tab>
    </template>

    <TabsPanels>
      <TabPanel :value="currentTab">
        <CardGrid :columns="4">
          <SuggestionCard icon="ion:cube" class="tw:h-full">
            <template #title>
              {{ $t("brands.home.cards.product.title") }}
            </template>

            <template #description>
              {{ $t("brands.home.cards.product.description") }}
            </template>

            <template #link>
              <Link
                :to="{
                  name: 'CreateProduct',
                }"
                icon="tabler-arrow-narrow-right"
              >
                {{ $t("brands.home.cards.product.link") }}
              </Link>
            </template>
          </SuggestionCard>

          <SuggestionCard icon="ic:round-people-alt" class="tw:h-full">
            <template #title
              >{{ $t("brands.home.cards.target-customer.title") }}
            </template>

            <template #description>
              {{ $t("brands.home.cards.target-customer.description") }}
            </template>

            <template #link>
              <Link
                :to="{
                  name: 'CreateBuyerPerson',
                }"
                icon="tabler-arrow-narrow-right"
              >
                {{ $t("brands.home.cards.target-customer.link") }}
              </Link>
            </template>
          </SuggestionCard>

          <Tooltip :disabled="!store.areProjectsDisabled">
            <SuggestionCard
              icon="tabler-file-filled"
              :disabled="store.areProjectsDisabled"
              class="tw:h-full"
            >
              <template #title>
                {{ $t("brands.home.cards.project.title") }}
              </template>

              <template #description>
                {{ $t("brands.home.cards.project.description") }}
              </template>

              <template #link>
                <Link
                  :to="{
                    name: 'CreateProject',
                  }"
                  icon="tabler-arrow-narrow-right"
                >
                  {{ $t("brands.home.cards.project.link") }}
                </Link>
              </template>
            </SuggestionCard>

            <template #content>
              {{ $t("brands.home.disabled-tooltips.projects") }}
            </template>
          </Tooltip>

          <Tooltip :disabled="!store.areUmbrellaCampaignsDisabled">
            <SuggestionCard
              icon="tabler-file-filled"
              :disabled="store.areUmbrellaCampaignsDisabled"
              class="tw:h-full"
            >
              <template #title>
                {{ $t("brands.home.cards.create-other-assets.title") }}
              </template>

              <template #description>
                {{ $t("brands.home.cards.create-other-assets.description") }}
              </template>

              <template #link>
                <Link
                  is="button"
                  icon="tabler-arrow-narrow-right"
                  @click="showCreateNewAssetModal = true"
                >
                  {{ $t("brands.home.cards.create-other-assets.link") }}
                </Link>
              </template>
            </SuggestionCard>

            <template #content>
              {{ $t("brands.home.disabled-tooltips.more-assets") }}
            </template>
          </Tooltip>

          <CreateNewAssetModal v-model="showCreateNewAssetModal" />
        </CardGrid>
      </TabPanel>
    </TabsPanels>
  </Tabs>
</template>
