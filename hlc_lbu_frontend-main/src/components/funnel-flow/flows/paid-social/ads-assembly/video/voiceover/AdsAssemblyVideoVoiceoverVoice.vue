<script setup lang="ts">
const props = defineProps<{
  name: string;
  /** The audio to play. Playing is disabled when the browser can't fetch it. */
  src?: string;
  /** Identifies the audio in the player, so only this item shows it playing. */
  playerKey: string;
  /** Shows the name as a button that emits `select`. */
  selectable?: boolean;
  selected?: boolean;
  /** Shows a button that emits `remove`. */
  removable?: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  select: [];
  remove: [];
  /** The audio couldn't be loaded or played, e.g. its link expired. */
  error: [];
}>();

const player = useAudioPlayerContext();

const canPlay = computed(() => isPlayableAudioUrl(props.src));
const isPlaying = computed(() => player.playingKey.value === props.playerKey);

function handleTogglePlay() {
  if (!isPlayableAudioUrl(props.src)) return;

  player.toggle(props.playerKey, props.src, () => emit("error"));
}
</script>

<template>
  <div
    class="tw:flex tw:min-w-0 tw:items-center tw:gap-3 tw:rounded-xl tw:border-2 tw:bg-white tw:px-3 tw:transition-colors"
    :class="selected ? 'tw:border-primary' : 'tw:border-gray-300'"
  >
    <button
      type="button"
      class="tw:flex tw:shrink-0 tw:text-[20px] tw:text-gray-900 tw:disabled:opacity-50"
      :class="{ 'tw:text-primary': isPlaying }"
      :disabled="!canPlay"
      :aria-label="
        isPlaying
          ? $t('funnel-flow.paid-social.ads.video.voiceover.voice.pause', {
              name,
            })
          : $t('funnel-flow.paid-social.ads.video.voiceover.voice.play', {
              name,
            })
      "
      @click="handleTogglePlay"
    >
      <Icon
        :icon="isPlaying ? 'tabler:player-pause-filled' : 'tabler:player-play'"
        aria-hidden="true"
      />
    </button>

    <button
      v-if="selectable"
      type="button"
      class="tw:min-w-0 tw:grow tw:truncate tw:py-2 tw:text-left tw:text-sm tw:font-semibold"
      :aria-pressed="selected"
      :disabled="disabled"
      :title="name"
      @click="emit('select')"
    >
      {{ name }}
    </button>

    <span
      v-else
      class="tw:min-w-0 tw:grow tw:truncate tw:py-2 tw:text-sm tw:font-semibold"
      :title="name"
    >
      {{ name }}
    </span>

    <button
      v-if="removable"
      type="button"
      class="tw:flex tw:shrink-0 tw:text-[20px] tw:text-gray-700 tw:hover:text-error tw:disabled:opacity-50"
      :disabled="disabled"
      :aria-label="
        $t('funnel-flow.paid-social.ads.video.voiceover.voice.remove', {
          name,
        })
      "
      @click="emit('remove')"
    >
      <Icon icon="tabler:trash" aria-hidden="true" />
    </button>
  </div>
</template>
