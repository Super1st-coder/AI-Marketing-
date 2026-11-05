<script setup lang="ts">
import { isChannelAttributeValid } from "@/services/funnel-flow/paid-social/AdsApi";

const store = useFunnelPaidSocialAdsAssemblyStore();

const attributesNames = ["primary_text", "headline", "description", "cta"];
const currentTab = ref<string>("primary_text");

function hasAlert(name: string) {
  return !isChannelAttributeValid(
    store.currentVariant?.channel_attributes?.find(
      (attribute) => attribute.name === name,
    ),
  );
}
</script>

<template>
  <Tabs v-model="currentTab" size="lg" class="tw:flex tw:grow tw:flex-col">
    <Container :maxWidth="1088">
      <TabsList>
        <Tab
          v-for="name in attributesNames"
          :value="name"
          :hasAlert="hasAlert(name)"
        >
          {{
            $t(`funnel-flow.paid-social.ads.channel-attributes.${name}.title`)
          }}
        </Tab>
      </TabsList>
    </Container>

    <TabPanel
      v-for="attribute in attributesNames"
      :value="attribute"
      class="tw:flex tw:grow tw:flex-col"
    >
      <AdsAssemblyEditorOverlayCaptionsTab :attributeName="attribute" />
    </TabPanel>
  </Tabs>
</template>
