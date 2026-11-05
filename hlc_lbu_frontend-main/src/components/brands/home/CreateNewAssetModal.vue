<script setup lang="ts">
import { RouteLocationRaw } from "vue-router";

const router = useRouter();
const isOpen = defineModel<boolean>({ required: true });
const { t } = useI18n();

const store = useBrandLayoutStore();

type SubModalName = "umbrellaCampaign" | "campaign" | "funnel";

type Option = {
  name: string;
  title: string;
  description: string;
  icon: string;
  to?: RouteLocationRaw;
  modal?: SubModalName;
  disabled?: boolean;
  disabledTooltip?: string;
};

const options = computed<Option[]>(() => [
  {
    name: "Product",
    title: t("brands.home.cards.product.title"),
    description: t("brands.home.cards.product.description"),
    icon: "ion:cube",
    to: { name: "CreateProduct" },
  },
  {
    name: "targetCustomer",
    title: t("brands.home.cards.target-customer.title"),
    description: t("brands.home.cards.target-customer.description"),
    icon: "ic:round-people-alt",
    to: { name: "CreateBuyerPerson" },
  },
  {
    name: "project",
    title: t("brands.home.cards.project.title"),
    description: t("brands.home.cards.project.description"),
    icon: "tabler-file-filled",
    to: { name: "CreateProject" },
  },
  {
    name: "umbrella-campaign",
    title: t("brands.home.cards.umbrella-campaign.title"),
    description: t("brands.home.cards.umbrella-campaign.description"),
    icon: "tabler-umbrella-filled",
    modal: "umbrellaCampaign",
  },
  {
    name: "campaign",
    title: t("brands.home.cards.campaign.title"),
    description: t("brands.home.cards.campaign.description"),
    icon: "tabler-speakerphone",
    modal: "campaign",
    disabled: store.areCampaignsDisabled,
    disabledTooltip: t("brands.home.disabled-tooltips.campaigns"),
  },
  {
    name: "funnel",
    title: t("brands.home.cards.funnel.title"),
    description: t("brands.home.cards.funnel.description"),
    icon: "tabler-speakerphone",
    modal: "funnel",
    disabled: store.areFunnelFlowsDisabled,
    disabledTooltip: t("brands.home.disabled-tooltips.funnels"),
  },
]);

const selectedOption = ref<Option>();

const generalErrorMessage = ref<string>();

const handleSelectOption = (option: Option) => {
  selectedOption.value = option;
  generalErrorMessage.value = undefined;
};

const handleCreate = () => {
  // Error validation
  if (!selectedOption.value) {
    generalErrorMessage.value = t(
      "brands.home.create-other-assets-modal.select-option-error",
    );
    return;
  }

  generalErrorMessage.value = undefined;

  // Logic to create a new asset based on the selected option
  if (selectedOption.value) {
    if (selectedOption.value.to) {
      // Navigate to the specified route
      router.push(selectedOption.value.to);
    }

    if (selectedOption.value.modal) {
      subModalOpen.value = selectedOption.value.modal;
    }
  }
};

watch(isOpen, (newVal) => {
  if (!newVal) {
    // Reset modal state when closed
    subModalOpen.value = undefined;
    generalErrorMessage.value = undefined;
    selectedOption.value = undefined;
  }
});

const subModalOpen = ref<SubModalName>();

const isUmbrellaCampaignModalOpen = computed({
  get: () => subModalOpen.value === "umbrellaCampaign",
  set: (value: boolean) => {
    subModalOpen.value = value ? "umbrellaCampaign" : undefined;
  },
});

const isCampaignModalOpen = computed({
  get: () => subModalOpen.value === "campaign",
  set: (value: boolean) => {
    subModalOpen.value = value ? "campaign" : undefined;
  },
});

const isFunnelModalOpen = computed({
  get: () => subModalOpen.value === "funnel",
  set: (value: boolean) => {
    subModalOpen.value = value ? "funnel" : undefined;
  },
});
</script>

<template>
  <Modal v-model="isOpen" :maxWidth="865" closeButton v-slot="{ close }">
    <ModalHeader>
      {{ $t("brands.home.create-other-assets-modal.title") }}

      <template #description>
        {{ $t("brands.home.create-other-assets-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <CardGrid :columns="3">
          <Tooltip
            v-for="option in options"
            :maxWidth="300"
            :disabled="!option.disabled"
          >
            <SuggestionCard
              is="button"
              :icon="option.icon"
              hoverColor="primary"
              :outlineColor="
                selectedOption?.name === option.name ? 'primary' : 'default'
              "
              :disabled="option.disabled"
              @click="handleSelectOption(option)"
              class="tw:h-full tw:w-full"
            >
              <template #title> {{ option.title }} </template>
              <template #description>
                {{ option.description }}
              </template>
            </SuggestionCard>

            <template #content>
              {{ option.disabledTooltip }}
            </template>
          </Tooltip>
        </CardGrid>

        <Alert v-if="generalErrorMessage" type="error" autoScroll>
          {{ generalErrorMessage }}
        </Alert>
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" @click="close">
        {{ $t("global.cancel") }}
      </Button>
      <Button @click="handleCreate">
        {{ $t("global.create") }}
      </Button>
    </ModalFooter>

    <CreateNewAssetModalUmbrellaCampaign
      v-model="isUmbrellaCampaignModalOpen"
    />

    <CreateNewAssetModalCampaign v-model="isCampaignModalOpen" />

    <CreateNewAssetModalFunnel v-model="isFunnelModalOpen" />
  </Modal>
</template>
