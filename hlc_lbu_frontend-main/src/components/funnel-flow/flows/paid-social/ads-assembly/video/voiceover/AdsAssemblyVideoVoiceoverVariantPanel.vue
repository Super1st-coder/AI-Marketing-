<script setup lang="ts">
import {
  GetVideoVoicesResponse,
  VideoScriptVariant,
  VideoVoice,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { VoiceoverVariantState, getShotClip } from "./voiceoverVariants";

const props = defineProps<{
  variant: VideoScriptVariant;
  state: VoiceoverVariantState;
  catalogue: GetVideoVoicesResponse;
  isLoadingVoices?: boolean;
  voicesErrorMessage?: string;
  /** Whether any variant is generating its audio. */
  isGeneratingAnyAudio?: boolean;
  isGeneratingCaptions?: boolean;
  captionsErrorMessage?: string;
}>();

const emit = defineEmits<{
  changeAccent: [accent: string];
  generateAudio: [];
  generateCaptions: [];
}>();

const selectedVoice = defineModel<VideoVoice | null>("selectedVoice", {
  required: true,
});
const addedVoices = defineModel<VideoVoice[]>("addedVoices", {
  required: true,
});

// Only one clip plays at a time in the variant. The panel unmounts on tab
// change, which stops the audio
useAudioPlayer();

const store = useFunnelPaidSocialAdsAssemblyStore();

function handleGoBack() {
  store.setPreviousVideoScreen("videoVoiceover");
}

const failedShotCount = computed(
  () => props.state.audio?.failedShotIndexes.length ?? 0,
);
</script>

<template>
  <div class="tw:flex tw:grow tw:flex-col">
    <Container class="tw:grow tw:pb-12" :maxWidth="910">
      <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6" borderRadius="md">
        <div>
          <h3 class="tw:mb-1 tw:text-xl tw:font-bold">
            {{ variant.title }}
          </h3>

          <Chip
            v-if="variant.persona"
            color="secondary"
            variant="outlined"
            size="md"
          >
            {{ variant.persona }}
          </Chip>
        </div>

        <Separator />

        <AdsAssemblyVideoVoiceoverVoices
          v-model:selectedVoice="selectedVoice"
          v-model:addedVoices="addedVoices"
          :catalogue="catalogue"
          :isLoadingVoices="isLoadingVoices"
          :voicesErrorMessage="voicesErrorMessage"
          :isGenerating="state.isGenerating"
          :errorMessage="state.errorMessage"
          @changeAccent="(accent) => emit('changeAccent', accent)"
          @generateAudio="emit('generateAudio')"
        />

        <Separator />

        <section class="tw:flex tw:flex-col tw:gap-4">
          <AdsAssemblyVideoLabel icon="tabler:microphone">
            <template #title>
              {{
                $t("funnel-flow.paid-social.ads.video.voiceover.shots-title")
              }}
            </template>
          </AdsAssemblyVideoLabel>

          <!-- The shots are collapsed, so the failures are summed up here -->
          <Alert v-if="failedShotCount" type="error">
            {{
              $t(
                "funnel-flow.paid-social.ads.video.voiceover.errors.shots-failed",
                { count: failedShotCount },
              )
            }}
          </Alert>

          <AccordionList>
            <AdsAssemblyVideoVoiceoverShot
              v-for="shot in variant.shots"
              :key="shot.index"
              :shot="shot"
              :clip="getShotClip(state.audio, shot.index)"
              :voice="state.audio?.voice"
              :failed="state.audio?.failedShotIndexes.includes(shot.index)"
              :playerKey="`clip:${variant.variant_id}:${shot.index}`"
            />
          </AccordionList>
        </section>
      </CardBase>

      <Alert
        v-if="captionsErrorMessage"
        type="error"
        autoScroll
        class="tw:mt-6"
      >
        {{ captionsErrorMessage }}
      </Alert>
    </Container>

    <AdsAssemblyVideoScriptsVariantPanelFooter>
      <template #before>
        <ButtonGoBack
          :disabled="isGeneratingAnyAudio || isGeneratingCaptions"
          @click="handleGoBack"
        />
      </template>

      <Button
        :disabled="isGeneratingAnyAudio"
        :isLoading="isGeneratingCaptions"
        @click="emit('generateCaptions')"
      >
        {{
          $t(
            "funnel-flow.paid-social.ads.video.voiceover.footer.generate-captions",
          )
        }}
      </Button>
    </AdsAssemblyVideoScriptsVariantPanelFooter>

    <!-- Warns before leaving the tab while its audio is generating -->
    <ModalFormSaveAlert :isDirty="state.isGenerating" />
  </div>
</template>
