<script setup lang="ts">
import {
  GetVideoVoicesResponse,
  VideoVoice,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { getListedVoices } from "./voiceoverVariants";
import { getVideoVoiceAccentLabel } from "../videoVoiceAccent";

const props = defineProps<{
  /** The voices of the accent picked. Shared by every variant. */
  catalogue: GetVideoVoicesResponse;
  isLoadingVoices?: boolean;
  voicesErrorMessage?: string;
  isGenerating?: boolean;
  errorMessage?: string;
}>();

const emit = defineEmits<{
  changeAccent: [accent: string];
  generateAudio: [];
}>();

const selectedVoice = defineModel<VideoVoice | null>("selectedVoice", {
  required: true,
});
const addedVoices = defineModel<VideoVoice[]>("addedVoices", {
  required: true,
});

const isDisabled = computed(() => props.isGenerating || props.isLoadingVoices);

const listedVoices = computed(() =>
  getListedVoices(addedVoices.value, props.catalogue.suggested),
);

function isAdded(voice: VideoVoice) {
  return addedVoices.value.some((added) => added.voice_id === voice.voice_id);
}

const accentOptions = computed(() =>
  props.catalogue.accents.map((accent) => ({
    value: accent,
    label: getVideoVoiceAccentLabel(accent),
  })),
);

function handleChangeAccent(accent: unknown) {
  if (typeof accent !== "string" || accent === props.catalogue.accent) return;

  emit("changeAccent", accent);
}

// `results` has every voice of the accent, so the search filters it here
// instead of asking the backend on every keystroke
const searchOptions = computed(() =>
  props.catalogue.results.map((voice) => ({
    value: voice.voice_id,
    label: voice.name,
  })),
);

const search = ref("");
const searchedVoiceId = ref<string>();

// A searched voice is added to the list, unless it's already there, and
// selected. The field is cleared so it can be searched again
watch(searchedVoiceId, async (voiceId) => {
  if (!voiceId) return;

  const voice = props.catalogue.results.find(
    (item) => item.voice_id === voiceId,
  );

  if (voice) {
    if (!listedVoices.value.some((item) => item.voice_id === voiceId)) {
      addedVoices.value = [voice, ...addedVoices.value];
    }

    selectedVoice.value = voice;
  }

  searchedVoiceId.value = undefined;
  search.value = "";
});

function handleRemove(voice: VideoVoice) {
  addedVoices.value = addedVoices.value.filter(
    (added) => added.voice_id !== voice.voice_id,
  );

  if (selectedVoice.value?.voice_id === voice.voice_id) {
    selectedVoice.value = null;
  }
}
</script>

<template>
  <section class="tw:flex tw:flex-col tw:gap-4">
    <AdsAssemblyVideoLabel icon="tabler:volume">
      <template #title>
        {{ $t("funnel-flow.paid-social.ads.video.voiceover.voice.title") }}
      </template>

      <template #description>
        {{
          $t("funnel-flow.paid-social.ads.video.voiceover.voice.description")
        }}
      </template>
    </AdsAssemblyVideoLabel>

    <div class="tw:flex tw:flex-col tw:gap-4 tw:xl:flex-row tw:xl:items-start">
      <FieldBaseAutocomplete
        v-model="searchedVoiceId"
        v-model:search="search"
        class="tw:grow tw:basis-0"
        name="voiceover-voice-search"
        :options="searchOptions"
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.video.voiceover.voice.search-placeholder',
          )
        "
        leftIcon="tabler:search"
        :disabled="isDisabled"
        hideLayout
        hideSelections
      />

      <FieldBaseNewSelect
        class="tw:xl:w-72"
        name="voiceover-voice-accent"
        :modelValue="catalogue.accent"
        :options="accentOptions"
        :placeholder="
          $t('funnel-flow.paid-social.ads.video.voiceover.voice.accent')
        "
        :clearable="false"
        :loading="isLoadingVoices"
        :disabled="isDisabled"
        hideLayout
        @update:modelValue="handleChangeAccent"
      />

      <Button
        class="tw:shrink-0"
        type="button"
        :disabled="!selectedVoice || isLoadingVoices"
        :isLoading="isGenerating"
        @click="emit('generateAudio')"
      >
        {{
          $t(
            "funnel-flow.paid-social.ads.video.voiceover.voice.generate-all-audio",
          )
        }}
      </Button>
    </div>

    <div>
      <p
        class="tw:mb-1 tw:text-xs tw:font-semibold tw:text-secondary-text tw:uppercase"
      >
        {{ $t("funnel-flow.paid-social.ads.video.voiceover.voice.suggested") }}
      </p>

      <ul
        v-if="listedVoices.length"
        class="tw:grid tw:grid-cols-1 tw:gap-4 tw:sm:grid-cols-2 tw:lg:grid-cols-4"
      >
        <li v-for="voice in listedVoices" :key="voice.voice_id">
          <AdsAssemblyVideoVoiceoverVoice
            :name="voice.name"
            :src="voice.preview_url"
            :playerKey="`preview:${voice.voice_id}`"
            selectable
            :selected="selectedVoice?.voice_id === voice.voice_id"
            :removable="isAdded(voice)"
            :disabled="isDisabled"
            @select="selectedVoice = voice"
            @remove="handleRemove(voice)"
          />
        </li>
      </ul>

      <p v-else class="tw:text-sm tw:text-secondary-text">
        {{ $t("funnel-flow.paid-social.ads.video.voiceover.voice.no-voices") }}
      </p>
    </div>

    <Alert v-if="voicesErrorMessage" type="error">
      {{ voicesErrorMessage }}
    </Alert>

    <Alert v-if="errorMessage" type="error" autoScroll>
      {{ errorMessage }}
    </Alert>
  </section>
</template>
