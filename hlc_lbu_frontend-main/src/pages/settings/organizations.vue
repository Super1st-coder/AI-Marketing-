<script setup lang="ts">
import AdminOrganizationsApi, {
  AdminOrganization,
} from "@/services/settings/AdminOrganizationsApi";
import AdminRolesApi, {
  AdminUserRole,
} from "@/services/settings/AdminRolesApi";

const { t } = useI18n();
usePageTitle(() => t("routes.user-settings-organizations"));

const { data: roles } = await AdminRolesApi.getList();

const search = ref("");
const page = ref(1);
const itemsPerPage = ref(10);
const items = ref<AdminOrganization[]>([]);
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
  const response = await AdminOrganizationsApi.getList({
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

  return { name: t("settings.organizations.page.unknown-role"), icon: "❓" };
}

const isAddModalOpen = ref(false);
const isDeleteModalOpen = ref(false);
const isEditModalOpen = ref(false);
const edit = ref<AdminOrganization>();

function handleEdit(organization: AdminOrganization) {
  edit.value = organization;
  isEditModalOpen.value = true;
}

function handleDelete(organization: AdminOrganization) {
  edit.value = organization;
  isDeleteModalOpen.value = true;
}
</script>

<template>
  <div class="tw:flex tw:h-full tw:flex-col tw:gap-6 tw:py-6 tw:pb-12">
    <!-- TODO: add help video URL later -->
    <PageTitle>
      {{ t("settings.organizations.page.title") }}

      <template #description>
        {{ t("settings.organizations.page.description") }}
      </template>
    </PageTitle>

    <CardBase>
      <VDataTableServer
        :headers="[
          {
            title: t('settings.organizations.page.headers.organization'),
            key: 'organization',
            sortable: false,
          },
          {
            title: t('settings.organizations.page.headers.role'),
            key: 'role',
            sortable: false,
          },
          {
            title: t('settings.organizations.page.headers.status'),
            key: 'status',
            sortable: false,
          },
          {
            title: t('settings.organizations.page.headers.actions'),
            key: 'actions',
            sortable: false,
            width: '140px',
          },
        ]"
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
              :placeholder="t('settings.organizations.page.search-placeholder')"
              class="tw:lg:basis-[250px]"
            />

            <PermissionGuard
              :requires="[{ name: 'ADMIN_ORG', actions: ['C'] }]"
            >
              <Button
                leftIcon="tabler-plus"
                variant="text"
                class="tw:self-end"
                @click="isAddModalOpen = true"
              >
                {{ t("settings.organizations.page.add-new-organization") }}
              </Button>
            </PermissionGuard>
          </div>

          <Separator />
        </template>

        <!-- Organization -->
        <template v-slot:item.organization="{ item }">
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
              :requires="[{ name: 'ADMIN_ORG', actions: ['U'] }]"
            >
              <button class="tw:text-2xl" @click="handleEdit(item)">
                <Icon icon="tabler-pencil" />
              </button>
            </PermissionGuard>

            <PermissionGuard
              :requires="[{ name: 'ADMIN_ORG', actions: ['D'] }]"
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

    <!-- Modal to create an organization -->
    <OrganizationModal v-model="isAddModalOpen" @success="refresh(true)" />

    <!-- Modal to edit an organization -->
    <OrganizationModal
      v-if="isEditModalOpen"
      v-model="isEditModalOpen"
      isEditing
      :data="edit"
      @success="refresh"
    />

    <!-- Modal to delete an organization -->
    <OrganizationDeleteModal
      v-if="edit"
      v-model="isDeleteModalOpen"
      :data="edit"
      @success="refresh"
    />
  </div>
</template>
