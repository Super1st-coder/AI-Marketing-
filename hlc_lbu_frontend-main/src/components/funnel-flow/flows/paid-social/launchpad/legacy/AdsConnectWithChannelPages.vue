<script setup lang="ts">
import ChannelConnections, {
  AdPage,
} from "@/services/funnel-flow/ChannelConnections";

const { goNext, goBack } = useMultiStepFormContext();

const adsConnection = adsConnectionStore();

let adPages: AdPage[] = [];

if (adsConnection?.connection === "meta-ads") {
  adPages = (await ChannelConnections.getAdPages()).data || [];
}

const metaAdsConnection = metaAdsConnectionStore();

const selectedAdPage = ref<string | null>(null);

function goWithSelectedPage() {
  if (!selectedAdPage.value) {
    console.log("Please select an ad page first.");
    return;
  }

  metaAdsConnection.setPageId(selectedAdPage.value);
}

const search = ref("");
const page = ref(1);
const itemsPerPage = ref(5);
</script>

<template>
  <FormStepLayout>
    <h1 class="tw:mb-0 tw:text-4xl tw:font-bold">
      Select Your Meta Business Page
    </h1>
    <p class="tw:text-secondary">
      Pick the Page where your ads will appear publicly.
    </p>
    <hr class="tw:border-secondary/30" />

    <CardBase
      v-if="adPages.length > 0 && adsConnection.connection === 'meta-ads'"
    >
      <VDataTable
        v-model:search="search"
        :items="adPages"
        :headers="[
          { title: '', key: 'select', sortable: false, width: 50 },
          { title: 'Facebook Page', key: 'name', sortable: false },
          { title: 'Page ID', key: 'id', sortable: false },
        ]"
      >
        <template #item.select="{ item }">
          <VRadio
            :value="item.id"
            v-model="selectedAdPage"
            color="primary"
            hide-details
            @click.stop="selectedAdPage = item.id"
          />
        </template>

        <template #item.name="{ item }">
          <div
            class="tw:flex tw:h-full tw:w-full tw:items-center"
            @click="selectedAdPage = item.id"
          >
            {{ item.name }}
          </div>
        </template>

        <template #item.id="{ item }">
          <div
            class="tw:flex tw:h-full tw:w-full tw:items-center"
            @click="selectedAdPage = item.id"
          >
            {{ item.id }}
          </div>
        </template>

        <template #bottom>
          <TablePagination
            v-model:page="page"
            :items-per-page="itemsPerPage"
            :total-items="adPages.length"
          />
        </template>
      </VDataTable>
    </CardBase>

    <template v-if="adsConnection.connection === 'google-ads'">
      <p class="tw:py-10 tw:text-center tw:text-secondary">
        Google Ads connection detected. No Page selection needed.
      </p>
    </template>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <Button
          :disabled="!selectedAdPage"
          @click="
            () => {
              goWithSelectedPage();
              goNext();
            }
          "
        >
          Select Page
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
