<script lang="ts" setup>
import { appLocales, appLocalesArray } from "@/plugins/i18n";

const router = useRouter();
const route = useRoute();

const authStore = useAuthStore();

const { locale: currentLocale } = useI18n({ useScope: "global" });

const store = useMenusStore();
const saveLockingStore = useSaveLockingStore();

async function handleLogout() {
  if ((await saveLockingStore.execute()) === "cancel") return;

  await authStore.logout();
}
</script>

<template>
  <nav
    :class="[
      'tw:sticky tw:top-0 tw:z-20 tw:flex tw:h-[66px] tw:items-center tw:gap-4',
      'tw:border-b tw:border-divider tw:bg-white tw:px-6',
    ]"
  >
    <button
      class="tw:h-full"
      :class="{
        'tw:hidden': !route.meta.hasSidebar,
        'tw:block tw:md:hidden': route.meta.hasSidebar,
      }"
      @click="store.toggleMenu"
    >
      <Icon icon="tabler-menu-2" class="tw:text-2xl" />
    </button>

    <RouterLink :to="{ name: 'BrandList' }">
      <img src="/images/logo-hiluca.png" alt="Logo Hiluca" class="tw:h-12" />
    </RouterLink>

    <div class="tw:grow">
      <slot />
    </div>

    <TopNavCreditsChip />

    <ButtonDropdown
      leftIcon="tabler:world"
      variant="label"
      color="primary"
      size="sm"
      type="button"
      placement="bottom-end"
    >
      {{ appLocales[currentLocale].code.toUpperCase() }}

      <template #options="{ close }">
        <ButtonDropdownOption
          v-for="locale in appLocalesArray"
          @click="
            () => {
              router.replace({
                params: { locale: locale.code },
                query: route.query,
                hash: route.hash,
              });
              close();
            }
          "
        >
          {{ locale.name }}
        </ButtonDropdownOption>
      </template>
    </ButtonDropdown>

    <ButtonDropdown
      variant="label"
      color="default"
      size="md"
      type="button"
      placement="bottom-end"
      class="tw:p-0!"
    >
      <AvatarIcon :initials="authStore.userInitials" />

      <template #options="{ close }">
        <div class="tw:px-5 tw:py-2">
          <AvatarProfile
            v-if="authStore.userFullname"
            :fullName="authStore.userFullname"
            :email="authStore.userEmail"
          />
        </div>

        <Separator />

        <ButtonDropdownOption :to="{ name: 'UserSettings' }">
          {{ $t("settings.title") }}
        </ButtonDropdownOption>

        <ButtonDropdownOption
          @click="
            handleLogout();
            close();
          "
        >
          <div class="tw:text-left">
            <span class="tw:block tw:font-normal">
              {{ $t("settings.logout") }}
            </span>
          </div>
        </ButtonDropdownOption>
      </template>
    </ButtonDropdown>
  </nav>
</template>
