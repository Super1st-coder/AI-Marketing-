<script setup lang="ts">
import type { SelectOption } from "@/components/forms/base/FieldBaseNewSelect.vue";
import LucaGuideOAuthApi from "@/services/guide/LucaGuideOAuthApi";
import LucaGuideOnboardingApi, {
  type LucaGuideMetaAdAccount,
} from "@/services/guide/LucaGuideOnboardingApi";
import {
  clearLucaGuideWorkspaceId,
  getLucaGuideWorkspaceId,
} from "@/utils/guide/workspace";

const { t } = useI18n();

const brandId = useBrandId();

const adAccountId = defineModel<string | undefined>("adAccountId");
const isConnected = defineModel<boolean>("connected", { default: false });

const emit = defineEmits<{
  connect: [];
}>();

const platform = ref("Meta Ads (Facebook & Instagram)");
const accounts = ref<LucaGuideMetaAdAccount[]>([]);
const isLoadingAccounts = ref(false);
const isConnecting = ref(false);
const isDisconnecting = ref(false);
const isDisconnectModalOpen = ref(false);
const generalErrorMessage = ref<string>();

const accountOptions = computed<SelectOption[]>(() =>
  accounts.value.map((account) => ({
    label: account.name ?? account.id,
    value: account.id,
    subtitle: `Ad account ID: ${account.id}`,
  })),
);

const selectedAdAccount = computed(() =>
  adAccountId.value
    ? accounts.value.find((account) => account.id === adAccountId.value)
    : undefined,
);

const isReady = computed(() => isConnected.value && Boolean(adAccountId.value));

async function fetchAdAccounts() {
  isLoadingAccounts.value = true;

  try {
    accounts.value = await LucaGuideOnboardingApi.listMetaAdAccounts();
  } finally {
    isLoadingAccounts.value = false;
  }
}

function getFacebookLoginReturnTo() {
  const url = new URL(window.location.href);
  url.search = "";
  return url.toString();
}

async function handleConnect() {
  generalErrorMessage.value = undefined;
  isConnecting.value = true;

  try {
    if (getLucaGuideWorkspaceId(brandId)) {
      const status = await LucaGuideOAuthApi.getFacebookStatus();

      if (!status.configured) {
        generalErrorMessage.value = t(
          "luca-guide.onboarding.meta-integration.not-configured",
        );
        isConnecting.value = false;
        return;
      }

      if (status.connected && !status.token_expired) {
        await fetchAdAccounts();
        isConnected.value = true;
        emit("connect");
        isConnecting.value = false;
        return;
      }
    }

    const response = await LucaGuideOAuthApi.getFacebookLoginUrl(
      getFacebookLoginReturnTo(),
    );

    if (!response.configured || !response.login_url) {
      generalErrorMessage.value = t(
        "luca-guide.onboarding.meta-integration.not-configured",
      );
      isConnecting.value = false;
      return;
    }

    window.location.assign(response.login_url);
  } catch (error) {
    console.error("Failed to start Facebook login:", error);
    generalErrorMessage.value = t("global.unexpected-error");
    isConnecting.value = false;
  }
}

async function handleDisconnect() {
  generalErrorMessage.value = undefined;
  isDisconnecting.value = true;

  try {
    await LucaGuideOnboardingApi.disconnect();
    clearLucaGuideWorkspaceId(brandId);
    window.location.reload();
  } catch (error) {
    console.error("Failed to disconnect Meta account:", error);
    generalErrorMessage.value = t("global.unexpected-error");
    isDisconnecting.value = false;
    return false;
  }
}

const meta = getLucaGuideWorkspaceId(brandId)
  ? await LucaGuideOnboardingApi.getMeta()
  : undefined;

if (meta?.status === "connected") {
  await fetchAdAccounts();
  adAccountId.value = meta.selected_ad_account_id ?? undefined;
}

isConnected.value = meta?.status === "connected";

defineExpose({
  isConnected,
  isReady,
  accounts,
  selectedAdAccount,
  accountOptions,
});
</script>

<template>
  <CardBase class="tw:grid tw:grid-cols-1 tw:gap-5 tw:p-6">
    <div class="tw:flex tw:items-center tw:justify-between">
      <h2 class="tw:text-xl tw:font-bold">
        {{ $t("channels.ad-channel-destination.title") }}
      </h2>

      <Chip v-if="isConnected" color="success" variant="label">
        {{ $t("channels.ad-channel-destination.connected") }}
      </Chip>
    </div>

    <Separator />

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:lg:grid-cols-2">
      <FieldBaseText
        v-model="platform"
        name="meta-platform"
        disabled
        leftIcon="tabler:brand-meta"
      />

      <Button
        v-if="isConnected"
        type="button"
        variant="label"
        @click="isDisconnectModalOpen = true"
      >
        {{ $t("channels.ad-channel-destination.disconnect-meta-ads-account") }}
      </Button>

      <Button
        v-else
        type="button"
        :isLoading="isConnecting"
        @click="handleConnect"
      >
        {{ $t("channels.ad-channel-destination.connect-meta-ads-account") }}
      </Button>
    </div>

    <div v-if="isConnected" class="tw:grid tw:grid-cols-1 tw:gap-5">
      <FieldBaseNewSelect
        v-model="adAccountId"
        name="ad_account"
        :placeholder="$t('channels.ad-channel-destination.select-ad-account')"
        :options="accountOptions"
        :disabled="isLoadingAccounts || isDisconnecting"
        chips
      >
        <template v-if="selectedAdAccount" #chip>
          <span class="tw:line-clamp-1">
            <span class="tw:text-primary-text">
              {{ selectedAdAccount.name ?? selectedAdAccount.id }}
            </span>
            {{ " " }}
            <span class="tw:text-gray-500"> ({{ adAccountId }}) </span>
          </span>
        </template>
        <template #hint>
          {{ $t("luca-guide.onboarding.meta-integration.helper") }}
        </template>
      </FieldBaseNewSelect>
    </div>

    <slot v-if="isConnected" name="footer" />
  </CardBase>

  <ModalGeneric
    v-model="isDisconnectModalOpen"
    :maxWidth="650"
    :confirmFn="handleDisconnect"
    :continueButtonProps="{ color: 'error' }"
  >
    <template #title>
      {{ $t("luca-guide.onboarding.meta-integration.disconnect.title") }}
    </template>

    <div class="tw:flex tw:flex-col tw:gap-4 tw:text-sm">
      <p class="tw:text-secondary-text">
        {{ $t("luca-guide.onboarding.meta-integration.disconnect.intro") }}
      </p>

      <ul class="tw:flex tw:flex-col tw:gap-3">
        <li class="tw:flex tw:items-start tw:gap-2">
          <Icon
            icon="tabler:trash"
            class="tw:mt-0.5 tw:shrink-0 tw:text-error"
          />
          <span>
            {{
              $t(
                "luca-guide.onboarding.meta-integration.disconnect.consequence-analysis",
              )
            }}
          </span>
        </li>
        <li class="tw:flex tw:items-start tw:gap-2">
          <Icon
            icon="tabler:cloud-off"
            class="tw:mt-0.5 tw:shrink-0 tw:text-error"
          />
          <span>
            {{
              $t(
                "luca-guide.onboarding.meta-integration.disconnect.consequence-data",
              )
            }}
          </span>
        </li>
        <li class="tw:flex tw:items-start tw:gap-2">
          <Icon
            icon="tabler:alert-triangle"
            class="tw:mt-0.5 tw:shrink-0 tw:text-error"
          />
          <span>
            {{
              $t(
                "luca-guide.onboarding.meta-integration.disconnect.consequence-undo",
              )
            }}
          </span>
        </li>
      </ul>

      <Alert type="info">
        {{
          $t("luca-guide.onboarding.meta-integration.disconnect.recommendation")
        }}
      </Alert>
    </div>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template #continue>
      {{ $t("luca-guide.onboarding.meta-integration.disconnect.confirm") }}
    </template>
  </ModalGeneric>
</template>
