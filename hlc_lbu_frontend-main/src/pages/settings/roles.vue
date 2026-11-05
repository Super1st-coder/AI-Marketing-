<script setup lang="ts">
import AdminRolesApi, {
  AdminRole,
  type AdminRoleDetail,
} from "@/services/settings/AdminRolesApi";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
usePageTitle(() => t("routes.user-settings-roles"));

const search = ref("");
const isEditModalOpen = ref(false);
const selectedRoleDetail = ref<AdminRoleDetail | undefined>(undefined);
const page = ref(1);
const itemsPerPage = ref(10);

const { data: roles } = await AdminRolesApi.getList();
const items = ref<AdminRole[]>(roles);

const tableHeaders = computed(() => [
  { title: t("global.role"), key: "name", sortable: false },
  { title: t("global.status"), key: "status", sortable: false },
  {
    title: t("global.actions"),
    key: "actions",
    sortable: false,
    width: "140px",
  },
]);

async function openEditModal(role: AdminRole) {
  const { data } = await AdminRolesApi.getOne(role.id);
  selectedRoleDetail.value = data;
  isEditModalOpen.value = true;
}
</script>

<template>
  <div class="tw:flex tw:h-full tw:flex-col tw:gap-6 tw:py-6 tw:pb-12">
    <!-- TODO: add help video URL later -->
    <PageTitle>
      {{ $t("global.roles") }}

      <template #description> {{ $t("settings.roles.description") }} </template>
    </PageTitle>

    <CardBase>
      <VDataTable
        v-model:search="search"
        v-model:page="page"
        :items="items"
        :itemsPerPage="itemsPerPage"
        :headers="tableHeaders"
      >
        <template #top>
          <div
            class="tw:flex tw:flex-col tw:px-8 tw:py-5 tw:lg:flex-row tw:lg:justify-end"
          >
            <FieldBaseText
              v-model="search"
              name="searchQuery"
              leftIcon="mdi-magnify"
              :placeholder="$t('settings.roles.search-placeholder')"
              class="tw:lg:basis-[250px]"
            />
          </div>

          <Separator />
        </template>

        <template v-slot:item.name="{ item }">
          <AdminRoleBadge :name="item.name" :icon="item.icon" />
        </template>

        <template v-slot:item.status="{ item }">
          <ChipStatus :status="item.status" />
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="tw:flex tw:gap-4">
            <button class="tw:text-2xl" @click="openEditModal(item)">
              <Icon icon="tabler-eye" />
            </button>
          </div>
        </template>

        <template #bottom>
          <TablePagination
            v-model:page="page"
            :itemsPerPage="itemsPerPage"
            :totalItems="items.length"
          />
        </template>
      </VDataTable>
    </CardBase>
  </div>

  <RoleModal
    v-if="selectedRoleDetail"
    v-model="isEditModalOpen"
    :role="selectedRoleDetail"
  />
</template>
