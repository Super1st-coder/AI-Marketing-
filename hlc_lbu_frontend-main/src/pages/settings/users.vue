<script setup lang="ts">
import AdminRolesApi, {
  AdminUser,
  AdminUserRole,
} from "@/services/settings/AdminRolesApi";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
usePageTitle(() => t("routes.user-settings-users"));

const { data: roles } = await AdminRolesApi.getList();

const tableHeaders = computed(() => [
  { title: t("global.user"), key: "user", sortable: false },
  { title: t("global.role"), key: "role", sortable: false },
  { title: t("global.status"), key: "status", sortable: false },
  {
    title: t("global.actions"),
    key: "actions",
    sortable: false,
    width: "140px",
  },
]);

const search = ref("");
const page = ref(1);
const itemsPerPage = ref(10);
const items = ref<AdminUser[]>([]);
const totalItems = ref(0);
const isLoading = ref(false);

// Reset to first page when search changes
watch(search, () => {
  page.value = 1;
});

// Fetch items from server
async function loadItems(options: {
  search: string;
  page: number;
  itemsPerPage: number;
}) {
  isLoading.value = true;

  // Fetch the items
  const start = (options.page - 1) * options.itemsPerPage;
  const end = options.page * options.itemsPerPage - 1;
  const response = await AdminRolesApi.getUserList({
    range: [start, end],
    filter: options.search ? { account: options.search } : undefined,
  });

  // Add a little bit of extra time to reduce flickering
  await sleep(500);

  items.value = response.data;
  totalItems.value = response.total;
  isLoading.value = false;
}

async function refresh(resetPage = false) {
  if (resetPage) {
    page.value = 1;
  }

  await loadItems({
    search: search.value,
    page: page.value,
    itemsPerPage: itemsPerPage.value,
  });
}

function getRoleBadgeProps(role: AdminUserRole) {
  const fullRole = roles.find((r) => r.id === role.id);

  if (fullRole) {
    return { name: fullRole.name, icon: fullRole.icon };
  }

  return { name: t("global.unknown"), icon: "❓" };
}

const isAddModalOpen = ref(false);
const isDeleteModalOpen = ref(false);
const isEditModalOpen = ref(false);
const userToEdit = ref<AdminUser>();

function handleEdit(user: AdminUser) {
  userToEdit.value = user;
  isEditModalOpen.value = true;
}

function handleDelete(user: AdminUser) {
  userToEdit.value = user;
  isDeleteModalOpen.value = true;
}
</script>

<template>
  <div class="tw:flex tw:h-full tw:flex-col tw:gap-6 tw:py-6 tw:pb-12">
    <!-- TODO: add help video URL later -->
    <PageTitle>
      {{ $t("global.users") }}

      <template #description>
        {{ $t("settings.users.description") }}
      </template>
    </PageTitle>

    <CardBase>
      <VDataTableServer
        :headers="tableHeaders"
        :items="items"
        :itemsLength="totalItems"
        :itemsPerPage="itemsPerPage"
        v-model:search="search"
        :loading="isLoading"
        :page="page"
        @update:options="loadItems"
      >
        <!-- Header -->
        <template #top>
          <div
            class="tw:flex tw:flex-col tw:px-8 tw:py-5 tw:lg:flex-row tw:lg:justify-end"
          >
            <FieldBaseText
              v-model="search"
              name="searchQuery"
              leftIcon="mdi-magnify"
              :placeholder="$t('settings.users.search-placeholder')"
              class="tw:lg:basis-[250px]"
            />

            <PermissionGuard
              :requires="[{ name: 'ADMIN_USER', actions: ['C'] }]"
            >
              <Button
                leftIcon="tabler-plus"
                variant="text"
                class="tw:self-end"
                @click="isAddModalOpen = true"
              >
                {{ $t("settings.users.add-new-user") }}
              </Button>
            </PermissionGuard>
          </div>

          <Separator />
        </template>

        <!-- User -->
        <template v-slot:item.user="{ item }">
          <AvatarProfile
            :fullName="item.extra_info.fullname"
            :email="item.account"
          />
        </template>

        <!-- Role -->
        <template v-slot:item.role="{ item }">
          <AdminRoleBadge
            v-for="role in item.roles"
            v-bind="getRoleBadgeProps(role)"
          />
        </template>

        <!-- Status -->
        <template v-slot:item.status="{ item }">
          <ChipStatus :status="item.status" />
        </template>

        <!-- Actions -->
        <template v-slot:item.actions="{ item }">
          <div class="tw:flex tw:gap-4">
            <PermissionGuard
              :requires="[{ name: 'ADMIN_USER', actions: ['U'] }]"
            >
              <button class="tw:text-2xl" @click="handleEdit(item)">
                <Icon icon="tabler-pencil" />
              </button>
            </PermissionGuard>

            <PermissionGuard
              :requires="[{ name: 'ADMIN_USER', actions: ['D'] }]"
            >
              <button class="tw:text-2xl" @click="handleDelete(item)">
                <Icon icon="tabler-trash" />
              </button>
            </PermissionGuard>
          </div>
        </template>

        <template #bottom>
          <TablePagination
            v-model:page="page"
            :items-per-page="itemsPerPage"
            :total-items="totalItems"
          />
        </template>
      </VDataTableServer>
    </CardBase>

    <!-- Modal to create a user -->
    <UserModal v-model="isAddModalOpen" @success="refresh(true)" />

    <!-- Modal to edit a user -->
    <UserModal
      v-if="isEditModalOpen"
      v-model="isEditModalOpen"
      isEditing
      :data="userToEdit"
      @success="refresh"
    />

    <!-- Modal to delete a user -->
    <UserDeleteModal
      v-if="userToEdit"
      v-model="isDeleteModalOpen"
      :data="userToEdit"
      @success="refresh"
    />
  </div>
</template>
