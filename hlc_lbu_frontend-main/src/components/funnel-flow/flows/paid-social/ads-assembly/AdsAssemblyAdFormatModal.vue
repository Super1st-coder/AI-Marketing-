<script setup lang="ts">
const props = defineProps<{ adGroupId: number }>();

const isOpen = defineModel<boolean>({ required: true });

const store = useFunnelPaidSocialAdsAssemblyStore();

function handleSelectStatic() {
  isOpen.value = false;
  store.moveToAdSet(props.adGroupId);
}

function handleSelectVideo() {
  isOpen.value = false;
  store.selectVideoFormatForAdSet(props.adGroupId);
}
</script>

<template>
  <Modal v-model="isOpen" :maxWidth="550" closeButton closeOnClickOutside>
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.ads.ad-groups.format-modal.title") }}

      <template #description>
        {{
          $t("funnel-flow.paid-social.ads.ad-groups.format-modal.description")
        }}
      </template>
    </ModalHeader>

    <ModalBody>
      <div class="tw:grid tw:grid-cols-1 tw:gap-4">
        <CardButton icon="tabler:photo" @click="handleSelectStatic">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.ads.ad-groups.format-modal.static.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.ad-groups.format-modal.static.description",
              )
            }}
          </template>
        </CardButton>

        <CardButton icon="tabler:video" @click="handleSelectVideo">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.ads.ad-groups.format-modal.ugc-video.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.ad-groups.format-modal.ugc-video.description",
              )
            }}
          </template>
        </CardButton>
      </div>
    </ModalBody>
  </Modal>
</template>
