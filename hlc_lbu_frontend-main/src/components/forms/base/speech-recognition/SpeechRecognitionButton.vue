<script lang="ts" setup>
import { appLocalesArray } from "@/plugins/i18n";
import UtilsApi from "@/services/UtilsApi";

const { locale } = useI18n();

const isPermissionDeniedModalOpen = ref(false);

const isRecording = ref(false);
const isLoading = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const audioChunks = ref<BlobPart[]>([]);
const canvas = ref<HTMLCanvasElement | null>(null);
const analyser = ref<AnalyserNode | null>(null);
const dataArray = ref<Uint8Array | null>(new Uint8Array(0));

const emit = defineEmits<{ textReady: [text: string] }>();
const mimeType = "audio/webm";

const getCanvasContext = () => {
  return canvas.value?.getContext("2d");
};

const draw = () => {
  // Request a render the next frame
  requestAnimationFrame(draw);

  // Get the canvas context
  const context = getCanvasContext();
  if (!canvas.value || !context || !dataArray.value || !analyser.value) {
    return;
  }

  // Clear canvas
  context.clearRect(0, 0, canvas.value.width, canvas.value.height);

  // Return if we are not recording
  if (!isRecording.value) {
    return;
  }

  const width = canvas.value.width;
  const height = canvas.value.height;

  if (dataArray.value) {
    analyser.value.getByteTimeDomainData(
      dataArray.value as Uint8Array<ArrayBuffer>,
    );
  }

  // Style of the graph
  context.lineWidth = 2;
  context.strokeStyle = "rgb(0, 0, 0)";

  // Start drawing the graph. It will be drawn using a single stroke.
  context.beginPath();
  let sliceWidth = (width * 1.0) / dataArray.value.length;
  let x = 0;

  // Draw each line in the graph
  for (let i = 0; i < dataArray.value.length; i++) {
    let value = dataArray.value[i] / 128.0;
    let y = (value * height) / 2;

    if (i === 0) {
      // Move to the first point
      context.moveTo(x, y);
    } else {
      // Draw the line to the next point
      context.lineTo(x, y);
    }

    x += sliceWidth;
  }

  // Draw the graph
  context.lineTo(canvas.value.width, canvas.value.height / 2);
  context.stroke();
};

// Begin drawing the graph
onMounted(() => {
  if (canvas.value) {
    draw();
  }
});

const startRecording = async () => {
  try {
    // Ask for microphone permission and get the media stream
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      isPermissionDeniedModalOpen.value = true;
      return;
    }
    mediaRecorder.value = new MediaRecorder(stream, { mimeType: mimeType });

    // Create an audio analyser to draw the graph
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    analyser.value = audioContext.createAnalyser();
    source.connect(analyser.value);
    analyser.value.fftSize = 512;
    dataArray.value = new Uint8Array(analyser.value.frequencyBinCount);

    // Add chunks
    mediaRecorder.value.ondataavailable = (event) => {
      audioChunks.value.push(event.data);
    };

    // When the recording stops
    mediaRecorder.value.onstop = async () => {
      isLoading.value = true;

      // Create Blob from the audio
      const audioBlob = new Blob(audioChunks.value, { type: mimeType });

      // Send request to process audio
      try {
        // Find the language name
        const language = appLocalesArray.find(
          (appLocale) => locale.value === appLocale.code,
        )?.apiName;

        // Make request
        const response = await UtilsApi.voiceToText(
          audioBlob,
          language ?? "English",
        );

        // Emit event
        emit("textReady", response.data.text);
      } catch (error) {
        console.error("Error uploading audio:", error);
      }

      // Clear
      isLoading.value = false;
      mediaRecorder.value = null;
      audioChunks.value = [];
      analyser.value = null;
      dataArray.value = null;

      // Stop the tracks - We need this so the browser doesn't keep using the microphone
      stream.getTracks().forEach((track) => {
        track.stop();
      });
    };

    // Start recordings
    mediaRecorder.value.start();
    isRecording.value = true;
  } catch (error) {
    console.error("Error accessing microphone:", error);
  }
};

const stopRecording = () => {
  if (mediaRecorder.value) {
    mediaRecorder.value.stop();
    isRecording.value = false;
    isLoading.value = true;
  }
};

const handleClick = async () => {
  // Workaround for: error TS2322: Type '"microphone"' is not assignable to type 'PermissionName'.
  const microphone = "microphone" as PermissionName;
  const microphonePermission = await navigator.permissions.query({
    name: microphone,
  });

  if (microphonePermission.state === "denied") {
    isPermissionDeniedModalOpen.value = true;
    return;
  }

  if (isRecording.value) {
    stopRecording();
  } else {
    startRecording();
  }
};
</script>

<template>
  <Button
    type="button"
    :icon="isRecording ? 'tabler-pause' : 'tabler-microphone'"
    :isLoading="isLoading"
    class="tw:relative"
    variant="label"
    :color="isRecording ? 'info' : 'primary'"
    square
    @click="handleClick"
    v-bind="$attrs"
  >
    <template #before>
      <canvas
        ref="canvas"
        width="48"
        height="48"
        class="tw:absolute tw:h-full tw:w-full"
      ></canvas>
    </template>
  </Button>

  <SpeechRecognitionButtonModal v-model="isPermissionDeniedModalOpen" />
</template>
