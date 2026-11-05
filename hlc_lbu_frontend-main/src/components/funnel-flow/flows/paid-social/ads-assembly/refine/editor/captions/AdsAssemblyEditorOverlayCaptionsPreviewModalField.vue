<script setup lang="ts">
import {
  AdChannelAttribute,
  AdChannelAttributePayload,
} from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{ attribute: AdChannelAttribute }>();

const model = defineModel<string | undefined>({ required: true });

const payloads = computed(() =>
  props.attribute.payloads
    .filter((payload): payload is AdChannelAttributePayload => Boolean(payload))
    .map((payload) => payload.payload),
);
const { currentIndex, move } = useSliderRef(payloads, 0);

watch(currentIndex, (newIndex) => {
  if (newIndex !== undefined) {
    model.value = payloads.value[newIndex];
  }
});
</script>

<template>
  <div>
    <div class="tw:mb-2 tw:flex tw:items-center">
      <FieldLabel class="tw:grow">
        {{
          $t(
            `funnel-flow.paid-social.ads.channel-attributes.${attribute.name}.label`,
          )
        }}
      </FieldLabel>

      <GeneratedValueSlider
        :currentIndex="currentIndex"
        :itemCount="attribute.payloads.length"
        @move="move"
      />
    </div>

    <FieldBaseTextarea
      v-if="attribute.type === 'text'"
      v-model="model"
      disabled
    />
    <FieldBaseText
      v-else-if="attribute.type === 'button'"
      v-model="model"
      disabled
    />
  </div>
</template>
