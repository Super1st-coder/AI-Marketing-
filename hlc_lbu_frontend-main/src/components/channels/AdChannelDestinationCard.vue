<script setup lang="ts">
import ChannelConnections, {
  AdAccount,
  AdPage,
} from "@/services/funnel-flow/ChannelConnections";
import { SelectOption } from "@/components/forms/base/FieldBaseNewSelect.vue";

const props = withDefaults(
  defineProps<{
    showPageSelect?: boolean;
  }>(),
  {
    showPageSelect: true,
  },
);

const adAccountId = defineModel<string | undefined>("adAccountId");
const pageId = defineModel<string | undefined>("pageId");
const authenticated = defineModel<boolean>("authenticated", { default: false });

const emit = defineEmits<{
  connect: [];
  disconnect: [];
}>();

const accounts = ref<AdAccount[]>([]);
const pages = ref<AdPage[]>([]);

const {
  isAuthenticated,
  platform,
  handleConnectWithFacebook,
  handleDisconnect: disconnectFacebookAuth,
} = await useMetaAdsFacebookAuth({
  onConnect: fetchConnectionData,
  onDisconnect: clearConnectionData,
});

watch(
  isAuthenticated,
  (value) => {
    authenticated.value = value;
  },
  { immediate: true },
);

const accountOptions = computed<SelectOption[]>(() =>
  accounts.value.map((account) => ({
    label: account.name,
    value: account.account_id,
    subtitle: `Ad account ID: ${account.account_id}`,
  })),
);

const pageOptions = computed<SelectOption[]>(() =>
  pages.value.map((page) => ({
    label: page.name,
    value: page.id,
  })),
);

const selectedAdAccount = computed(() =>
  adAccountId.value
    ? accounts.value.find((account) => account.account_id === adAccountId.value)
    : undefined,
);

async function fetchAdAccounts() {
  const { data } = await ChannelConnections.getAdAccounts();
  accounts.value = data;
}

async function fetchBusinessPages() {
  if (!props.showPageSelect) {
    return;
  }

  const { data } = await ChannelConnections.getAdPages();
  pages.value = data;
}

async function fetchConnectionData() {
  await Promise.all([fetchAdAccounts(), fetchBusinessPages()]);
  emit("connect");
}

function clearConnectionData() {
  accounts.value = [];
  pages.value = [];
  adAccountId.value = undefined;
  pageId.value = undefined;
  emit("disconnect");
}

async function handleDisconnect() {
  await disconnectFacebookAuth();
}

const isReady = computed(
  () =>
    isAuthenticated.value &&
    Boolean(adAccountId.value) &&
    (!props.showPageSelect || Boolean(pageId.value)),
);

if (isAuthenticated.value) {
  await fetchConnectionData();
}

defineExpose({
  isAuthenticated,
  isReady,
  accounts,
  pages,
  accountOptions,
  pageOptions,
});
</script>

<template>
  <CardBase class="tw:grid tw:grid-cols-1 tw:gap-5 tw:p-6">
    <div class="tw:flex tw:items-center tw:justify-between">
      <h2 class="tw:text-xl tw:font-bold">
        {{ $t("channels.ad-channel-destination.title") }}
      </h2>

      <Chip v-if="isAuthenticated" color="success" variant="label">
        {{ $t("channels.ad-channel-destination.connected") }}
      </Chip>
    </div>

    <Separator />

    <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:lg:grid-cols-2">
      <FieldBaseText v-model="platform" disabled leftIcon="tabler:brand-meta" />

      <Button
        v-if="isAuthenticated"
        type="button"
        variant="label"
        @click="handleDisconnect"
      >
        {{ $t("channels.ad-channel-destination.disconnect-meta-ads-account") }}
      </Button>

      <Button v-else type="button" @click="handleConnectWithFacebook">
        {{ $t("channels.ad-channel-destination.connect-meta-ads-account") }}
      </Button>
    </div>

    <div
      v-if="isAuthenticated"
      class="tw:grid tw:grid-cols-1 tw:gap-5"
      :class="{ 'tw:lg:grid-cols-2': showPageSelect }"
    >
      <slot
        name="selectors"
        :account-options="accountOptions"
        :page-options="pageOptions"
        :accounts="accounts"
      >
        <FieldBaseNewSelect
          v-model="adAccountId"
          name="ad_account"
          :placeholder="$t('channels.ad-channel-destination.select-ad-account')"
          :options="accountOptions"
          chips
        >
          <template v-if="selectedAdAccount" #chip>
            <span class="tw:line-clamp-1">
              <span class="tw:text-primary-text">
                {{ selectedAdAccount.name }}
              </span>
              {{ " " }}
              <span class="tw:text-gray-500"> ({{ adAccountId }}) </span>
            </span>
          </template>
        </FieldBaseNewSelect>

        <FieldBaseNewSelect
          v-if="showPageSelect"
          v-model="pageId"
          name="business_page"
          :placeholder="
            $t('channels.ad-channel-destination.select-business-page')
          "
          :options="pageOptions"
        />
      </slot>
    </div>

    <slot v-if="isAuthenticated" name="footer" />
  </CardBase>
</template>
