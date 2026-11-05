<script setup lang="ts">
import ChannelConnections, {
  AdAccount,
} from "@/services/funnel-flow/ChannelConnections";

const { goNext, goBack, currentFlatStepIndex, goToStep } =
  useMultiStepFormContext();

const metaAdsConnection = metaAdsConnectionStore();
const googleAdsConnection = googleAdsConnectionStore();
const adsConnection = adsConnectionStore();
// const authStore = useAuthStore();

let adAccounts: AdAccount[];
const selectedAdAccount = ref<string | null>(null);

if (adsConnection.connection === "google-ads") {
  // const GoogleAdsCustomerList = await ChannelConnections.getCustomersListInfo(
  //   authStore.userEmail!,
  // );
  // adAccounts = GoogleAdsCustomerList.customers.map((account: any) => ({
  //   name: account.name,
  //   account_id: account.id,
  // }));
} else if (adsConnection.connection === "meta-ads") {
  adAccounts = (await ChannelConnections.getAdAccounts()).data;
}

function goWithSelectedAccount() {
  if (!selectedAdAccount.value) {
    console.log("Please select an ad account first.");
    return;
  }

  if (adsConnection.connection === "meta-ads") {
    metaAdsConnection.setAdAccountId(selectedAdAccount.value);
  } else {
    googleAdsConnection.setCustomerId(selectedAdAccount.value);
  }

  if (adsConnection.connection === "google-ads") {
    const currentStepIndex = currentFlatStepIndex.value;
    goToStep(currentStepIndex + 2);
  } else {
    goNext();
  }
}

const search = ref("");
const page = ref(1);
const itemsPerPage = ref(10);

const paginatedAccounts = computed(() => {
  const start = (page.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return adAccounts.slice(start, end);
});

function goBackChannelAdAccounts() {
  if (adsConnection.connection === "meta-ads") {
    const currentStepIndex = currentFlatStepIndex.value;
    goToStep(currentStepIndex - 2);
  } else if (adsConnection.connection === "google-ads") {
    goBack();
  }
}
</script>

<template>
  <FormStepLayout>
    <h1 class="tw:mb-0 tw:text-4xl tw:font-bold">
      Select Your
      {{ adsConnection.connection === "meta-ads" ? "Meta" : "Google" }} Ads
      Account
    </h1>
    <p class="tw:text-secondary">
      Choose which ad account you want to connect and launch from.
    </p>
    <hr class="tw:border-secondary/30" />

    <CardBase>
      <VDataTable
        v-model:search="search"
        :items="paginatedAccounts"
        :headers="[
          { title: '', key: 'select', sortable: false, width: 50 },
          { title: 'Account Name', key: 'name', sortable: false },
          { title: 'Account ID', key: 'account_id', sortable: false },
        ]"
      >
        <template #item="{ item }">
          <tr @click="selectedAdAccount = item.account_id">
            <td>
              <VRadio
                :value="item.account_id"
                v-model="selectedAdAccount"
                color="primary"
                hide-details
              />
            </td>
            <td>{{ item.name }}</td>
            <td>{{ item.account_id }}</td>
          </tr>
        </template>

        <template #bottom>
          <TablePagination
            v-model:page="page"
            :items-per-page="itemsPerPage"
            :total-items="adAccounts.length"
          />
        </template>
      </VDataTable>
    </CardBase>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBackChannelAdAccounts" />
        <Button :disabled="!selectedAdAccount" @click="goWithSelectedAccount">
          Connect Account
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
