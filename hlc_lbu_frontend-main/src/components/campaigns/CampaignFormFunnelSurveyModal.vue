<script setup lang="ts">
import { IconCardVariant } from "../cards/IconCard.vue";

const isOpen = defineModel<boolean>({ required: true });

const isSending = ref(false);

const options = [
  {
    value: "activation",
    label: "Activation",
    icon: "tabler-bolt",
    color: "primary",
  },
  {
    value: "retention",
    label: "Retention",
    icon: "tabler-lock",
    color: "error",
  },
  {
    value: "revenue",
    label: "Revenue",
    icon: "tabler-coin",
    color: "success",
  },
  {
    value: "referral",
    label: "Referral",
    icon: "tabler-link",
    color: "info",
  },
];

const selectedCards = ref<string[]>([]);

const close = () => {
  isOpen.value = false;
};

const handleSend = async () => {
  isSending.value = true;

  console.log(selectedCards.value);
  await sleep(1000);

  isSending.value = false;
  close();
};
</script>

<template>
  <Modal v-model="isOpen" class="tw:max-w-[712px] tw:p-10" closeButton>
    <h2 class="tw:text-4xl tw:font-extrabold">Lorem ipsum dolor sit amet</h2>
    <p class="tw:mb-10 tw:text-secondary-text">
      Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
      tempor incididunt ut labore et dolore magna aliqua.
    </p>

    <div class="tw:mb-10 tw:grid tw:grid-cols-2 tw:gap-6">
      <label
        v-for="item in options"
        :key="item.value"
        class="tw:flex tw:cursor-pointer tw:items-center tw:justify-between tw:rounded-[20px] tw:p-4 tw:shadow-[0_8px_16px] tw:shadow-primary-text/8"
      >
        <span class="tw:flex tw:items-center tw:gap-4">
          <IconCard
            :icon="item.icon"
            :variant="item.color as IconCardVariant"
          />
          <span class="tw:text-lg tw:font-extrabold">{{ item.label }}</span>
        </span>

        <input
          type="checkbox"
          name="funnel"
          :value="item.value"
          v-model="selectedCards"
          class="tw:h-[18px] tw:w-[18px] tw:border-2 tw:border-error"
        />
      </label>
    </div>

    <div class="tw:grid tw:grid-cols-2 tw:gap-8">
      <Button type="button" variant="outlined" @click="close">
        {{ $t("global.skip") }}
      </Button>

      <Button
        type="button"
        color="primary"
        @click="handleSend"
        :isLoading="isSending"
      >
        {{ $t("global.send") }}
      </Button>
    </div>
  </Modal>
</template>
