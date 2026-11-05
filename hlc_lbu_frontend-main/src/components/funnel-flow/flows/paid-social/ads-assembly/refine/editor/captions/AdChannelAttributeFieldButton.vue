<script setup lang="ts">
import { startCase } from "lodash";

import { SelectOption } from "@/components/forms/base/select-option";
import { META_AD_CTA_OPTIONS } from "@/constants/meta-ads/cta";
import { AdChannelAttribute } from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{
  index: number;
  name: string;
  canBeDeleted?: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{ delete: [] }>();

const { t, te } = useI18n();

const channelAttribute = useFieldValue<AdChannelAttribute>(() => props.name);

const currentCta = useFieldValue<string | null | undefined>(
  () => `${props.name}.payloads[${props.index}].payload`,
);

function getCtaLabel(value: string) {
  const translationKey = `meta-ads.cta.options.${value}`;

  // Without a translation, title-case the code (e.g. CTA_LABEL -> Cta Label)
  return te(translationKey)
    ? t(translationKey)
    : startCase(value.toLowerCase());
}

const ctas = computed(() => {
  const options = META_AD_CTA_OPTIONS.map<SelectOption>((value) => ({
    label: getCtaLabel(value),
    value,
  }));

  // The back-end can generate CTAs this list doesn't know about yet. Keep the
  // current value as an option so it shows a readable label and can be replaced.
  const current = currentCta.value;
  if (current && !options.some(({ value }) => value === current)) {
    options.push({ label: getCtaLabel(current), value: current });
  }

  return options;
});
</script>

<template>
  <div :class="{ 'tw:pointer-events-none tw:opacity-50': disabled }">
    <FieldLabel v-if="index === 0">
      {{
        $t(
          `funnel-flow.paid-social.ads.channel-attributes.${channelAttribute.name}.label`,
        )
      }}
    </FieldLabel>

    <div class="tw:flex tw:items-start tw:gap-2">
      <FieldAutocomplete
        :name="`${props.name}.payloads[${index}].payload`"
        :placeholder="
          $t(
            `funnel-flow.paid-social.ads.channel-attributes.${channelAttribute.name}.placeholder`,
          )
        "
        :options="ctas"
        clearable
        required
        class="tw:grow"
      />

      <Tooltip v-if="index === 0" placement="top">
        <Button
          type="button"
          variant="label"
          color="primary"
          icon="custom:pin-filled"
          :shadow="false"
          disabled
        />

        <template #content>
          {{ $t("funnel-flow.paid-social.ads.refine.editor.pinned-format") }}
        </template>
      </Tooltip>

      <Button
        v-else-if="canBeDeleted"
        type="button"
        variant="outlined"
        color="secondary"
        icon="tabler-x"
        @click="emit('delete')"
      />
    </div>
  </div>
</template>
