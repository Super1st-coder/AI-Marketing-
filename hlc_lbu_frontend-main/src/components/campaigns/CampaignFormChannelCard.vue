<script setup lang="ts">
import { ChannelGroupData } from "@/services/UtilsApi";
import { groupChannelStyles } from "../../constants/campaigns";

const props = defineProps<{
  channelGroup: ChannelGroupData;
  name: string;
}>();

const { value: selectedFunnelId } = useField<number[]>(() => props.name);
</script>

<template>
  <CardBase
    class="tw:relative tw:flex tw:flex-col tw:gap-5 tw:p-4"
    :class="{
      'tw:cursor-pointer': channelGroup.active,
      'tw:opacity-75': !channelGroup.active,
    }"
    :hoverColor="!channelGroup.active ? undefined : 'primary'"
    :color="
      selectedFunnelId.find((id) => id === channelGroup.id)
        ? 'primary'
        : 'default'
    "
  >
    <CardTitle
      :icon="groupChannelStyles[channelGroup.name]?.icon"
      :iconVariant="groupChannelStyles[channelGroup.name]?.color"
    >
      {{ $t(`channel-groups.${channelGroup.name}.title`) }}
    </CardTitle>

    <p class="tw:text-sm">
      {{ $t(`channel-groups.${channelGroup.name}.description`) }}
    </p>

    <Separator />

    <p v-if="groupChannelStyles[channelGroup.name]">
      <strong>{{ $t("campaigns.channel-card.top-channels") }}: </strong>
      {{
        groupChannelStyles[channelGroup.name].topChannels
          .map((channel) => $t(`channels.${channel}`))
          .join(", ")
      }}
    </p>

    <Chip v-if="!channelGroup.active" class="tw:absolute tw:top-5 tw:right-5">
      Soon
    </Chip>
  </CardBase>
</template>
