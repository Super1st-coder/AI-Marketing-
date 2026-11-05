import { InjectionKey, Ref } from "vue";

/** Plays one clip at a time across a component and its descendants. */
export type AudioPlayer = {
  /** Key of the clip playing, if any. */
  playingKey: Readonly<Ref<string | undefined>>;
  /**
   * Plays the clip, or pauses it if it's the one playing. `onError` is called
   * if the clip can't be loaded or played, e.g. when its link expired.
   */
  toggle: (key: string, src: string, onError?: () => void) => void;
  stop: () => void;
};

const audioPlayerInjectionKey: InjectionKey<AudioPlayer> =
  Symbol("audioPlayer");

/**
 * Whether the browser can fetch the URL. Some APIs return URLs that only the
 * server can read, like `file://`.
 */
export function isPlayableAudioUrl(url: string | undefined): url is string {
  return Boolean(url && /^(https?|blob|data):/.test(url));
}

/**
 * Creates a player and provides it to the component's descendants, which get
 * it with `useAudioPlayerContext`. Starting a clip stops the one playing.
 */
export function useAudioPlayer(): AudioPlayer {
  const audio = new Audio();
  const loadedKey = ref<string>();
  const isPlaying = ref(false);
  // The `onError` of the clip loaded
  let handleLoadedError: (() => void) | undefined;

  audio.addEventListener("play", () => {
    isPlaying.value = true;
  });
  audio.addEventListener("pause", () => {
    isPlaying.value = false;
  });
  audio.addEventListener("ended", () => {
    isPlaying.value = false;
  });
  audio.addEventListener("error", () => {
    console.error("Failed to load the audio:", audio.error);
    isPlaying.value = false;
    loadedKey.value = undefined;
    handleLoadedError?.();
    handleLoadedError = undefined;
  });

  async function play() {
    try {
      await audio.play();
    } catch (error) {
      // Playing something else interrupts the pending play
      if (error instanceof DOMException && error.name === "AbortError") return;

      console.error("Failed to play the audio:", error);
      isPlaying.value = false;
    }
  }

  function toggle(key: string, src: string, onError?: () => void) {
    if (loadedKey.value === key) {
      if (audio.paused) {
        play();
      } else {
        audio.pause();
      }

      return;
    }

    loadedKey.value = key;
    handleLoadedError = onError;
    audio.src = src;
    play();
  }

  function stop() {
    audio.pause();
  }

  onBeforeUnmount(() => {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  });

  const player: AudioPlayer = {
    playingKey: computed(() => (isPlaying.value ? loadedKey.value : undefined)),
    toggle,
    stop,
  };

  provide(audioPlayerInjectionKey, player);

  return player;
}

/** The player provided by `useAudioPlayer` in an ancestor. */
export function useAudioPlayerContext(): AudioPlayer {
  const player = inject(audioPlayerInjectionKey);
  if (!player) {
    throw new Error(
      "useAudioPlayerContext needs useAudioPlayer in an ancestor",
    );
  }

  return player;
}
