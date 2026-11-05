<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import AdsApi, {
  AdChannelAttribute,
  AdChannelAttributePayload,
} from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{
  name: string;
  disabled?: boolean;
}>();

const store = useFunnelPaidSocialAdsAssemblyStore();
const { t } = useI18n();

const generalErrorMessage = ref<string | undefined>(undefined);

const channelAttribute = useFieldValue<AdChannelAttribute>(() => props.name);
const payloadsField = useFieldArray<{
  id: number;
  payload?: string;
}>(() => `${props.name}.payloads`);
const isGeneratingAllTexts = ref(false);
const bulkGeneratedSlices = ref<string[][]>([]);

const min = computed(() => channelAttribute.value.min);
const max = computed(() => channelAttribute.value.max);
const remainingToReachMax = computed(
  () => max.value - channelAttribute.value.payloads.length,
);

function addField() {
  if (payloadsField.fields.value.length < max.value) {
    payloadsField.push({
      id: payloadsField.fields.value.length,
      payload: undefined,
    });
  }
}

function addRemainingFields() {
  if (payloadsField.fields.value.length < max.value) {
    const remaining = remainingToReachMax.value;

    for (let index = 0; index < remaining; index++) {
      payloadsField.push({
        id: payloadsField.fields.value.length,
        payload: "",
      });
    }
  }
}

function removeField(index: number) {
  if (payloadsField.fields.value.length > min.value) {
    // Remove the index
    payloadsField.remove(index);

    // Rewrite the ids
    payloadsField.replace(
      payloadsField.fields.value.map(({ value: { payload } }, index) => ({
        id: index,
        payload,
      })),
    );
  }
}

async function handleGenerateSingleText(channelAttribute: AdChannelAttribute) {
  if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
    throw new UnidentifiedError();
  }

  // Generate texts
  const { data: response } = await AdsApi.generateTextForAdChannelAttribute(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    {
      attribute: channelAttribute,
    },
  );

  return response.payload;
}

async function handleGenerateAllTexts() {
  try {
    if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
      throw new UnidentifiedError();
    }

    isGeneratingAllTexts.value = true;
    generalErrorMessage.value = undefined;

    // The generate endpoint only generates texts for the payloads present in the attributes
    // but we want to generate all the payloads, wheter the user have added just one or two, etc.
    // So here we fill in the payload array with the other items to reach "max" possible payloads.
    const attributes =
      store.currentVariant?.channel_attributes?.map((attribute) => {
        if (attribute.name === channelAttribute.value.name) {
          const payloads = Array.from(
            { length: max.value },
            (_, index) =>
              ({
                id: index,
                payload: channelAttribute.value.payloads[index]?.payload ?? "",
              }) as AdChannelAttributePayload,
          );

          return { ...channelAttribute.value, payloads };
        }

        return attribute;
      }) ?? [];

    // Generate texts
    const { data: response } = await AdsApi.generateTextsForAdChannelAttributes(
      store.brandId,
      store.campaignId,
      store.currentAd.ad_id,
      store.currentChannel.channel_id,
      store.currentVariant.id,
      {
        attributes,
      },
    );

    // Find the payloads we are gonna use in the response
    const targetPayloads = response
      .find((attribute) => attribute.name === channelAttribute.value.name)
      ?.payloads.map((payloads) => payloads.payload);

    if (!targetPayloads) {
      return;
    }

    bulkGeneratedSlices.value = targetPayloads;

    // Replace main payloads
    payloadsField.replace(
      targetPayloads.map((payloads, index) => ({
        id: index,
        payload: payloads[0],
      })),
    );
  } catch (e: unknown) {
    console.error(e);

    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.generate-text-error",
    );
  } finally {
    isGeneratingAllTexts.value = false;
  }
}

const isDisabled = computed(() => props.disabled || isGeneratingAllTexts.value);
</script>

<template>
  <div class="tw:grid tw:grid-cols-1 tw:gap-6">
    <template v-for="(_payload, index) in payloadsField.fields.value">
      <AdChannelAttributeFieldText
        v-if="channelAttribute.type === 'text'"
        :name="name"
        :index="index"
        :canBeDeleted="payloadsField.fields.value.length > 1"
        :generateFn="handleGenerateSingleText"
        :bulkGeneratedTexts="bulkGeneratedSlices[index]"
        :disabled="isDisabled"
        @delete="removeField(index)"
      />
      <AdChannelAttributeFieldButton
        v-if="channelAttribute.type === 'button'"
        :name="name"
        :index="index"
        :canBeDeleted="payloadsField.fields.value.length > 1"
        :disabled="isDisabled"
        @delete="removeField(index)"
      />
    </template>

    <Separator />

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <div class="tw:flex tw:flex-col tw:gap-3 tw:md:flex-row">
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        :leftIcon="remainingToReachMax > 0 ? 'tabler:plus' : undefined"
        size="md"
        :uppercase="false"
        :disabled="payloadsField.fields.value.length >= max || isDisabled"
        @click="addField"
      >
        <template v-if="remainingToReachMax === 0">
          {{
            $t("funnel-flow.paid-social.ads.refine.editor.limit-reached", {
              current: max,
              max: max,
            })
          }}
        </template>
        <template v-else>
          {{
            $t(
              "funnel-flow.paid-social.ads.refine.editor.add-single-attribute",
              {
                label: $t(
                  `funnel-flow.paid-social.ads.channel-attributes.${channelAttribute.name}.label`,
                ),
              },
            )
          }}
        </template>
      </Button>

      <Button
        v-if="remainingToReachMax > 1"
        type="button"
        variant="label"
        color="primary"
        leftIcon="tabler:plus"
        size="md"
        :uppercase="false"
        :disabled="payloadsField.fields.value.length >= max || isDisabled"
        @click="addRemainingFields"
      >
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.add-multiple-attribute",
            {
              count: remainingToReachMax,
              label: $t(
                `funnel-flow.paid-social.ads.channel-attributes.${channelAttribute.name}.label`,
              ),
            },
          )
        }}
      </Button>

      <div class="tw:grow"></div>

      <Button
        type="button"
        color="primary"
        leftIcon="tabler:plus"
        size="md"
        :uppercase="false"
        :isLoading="isGeneratingAllTexts"
        :disabled="isDisabled"
        @click="handleGenerateAllTexts"
      >
        {{
          $t("funnel-flow.paid-social.ads.refine.editor.generate-all-copies")
        }}
      </Button>
    </div>
  </div>
</template>
