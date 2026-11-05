<script setup lang="ts">
import { googleDriveAdminStore } from "@/stores/GoogleDriveAdminStore";
import { useImageLibraryStore } from "@/stores/ImageLibraryStore";
import { useObjectUrl } from "@vueuse/core";
import { object, string } from "yup";
import { ref, nextTick, onMounted } from "vue";
import ModalImageCropper from "@/components/modals/ModalImageCropper.vue";

interface Props {
  accept?: string;
  cropper?: boolean;
  aspectRatio?: number;
  disabled?: boolean;
}

const props = defineProps<Props>();

const isLoadingForAuth = ref(false);
const isCropperModalOpen = ref(false);
const currentView = ref<"picker" | "confirm">("picker");

const selectedFile = ref<any | null>(null);
const pendingFile = ref<File | null>(null);
const croppedFile = ref<File | null>(null);
const selectedImage = ref<string | null>(null);

const customName = ref("");
const customNameError = ref("");
const previewUrl = useObjectUrl(croppedFile);
const driveAuth = googleDriveAdminStore();
const { t } = useI18n();

const API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const SCOPES = [
  "https://www.googleapis.com/auth/drive.readonly",
  "https://www.googleapis.com/auth/drive.file",
];

function loadGapi(callback: () => void) {
  const script = document.createElement("script");
  script.src = "https://apis.google.com/js/api.js";
  script.onload = () => {
    gapi.load("client:auth2", callback);
  };
  document.body.appendChild(script);
}

async function linkAccount() {
  isLoadingForAuth.value = true;
  if (!window.gapi) {
    loadGapi(() => startPicker(false));
  } else {
    startPicker(false);
  }
}

function startPicker(forceAuth = false) {
  if (driveAuth.accessToken && !forceAuth) {
    if (driveAuth.isTokenExpired()) {
      startPicker(true);
    } else {
      openPicker(driveAuth.accessToken);
    }
    isLoadingForAuth.value = false;
    return;
  }

  const tokenClient = google.accounts.oauth2.initTokenClient({
    client_id: CLIENT_ID,
    scope: SCOPES.join(" "),
    callback: (response) => {
      clearTimeout(authTimeout);
      if (response.error) {
        console.warn("Auth failed:", response.error);
        isLoadingForAuth.value = false;
        return;
      }

      if (response.access_token) {
        const expiresAt = Date.now() + response.expires_in * 1000;
        driveAuth.setToken(response.access_token, expiresAt);
        openPicker(driveAuth.accessToken!);
      }

      isLoadingForAuth.value = false;
    },
  });

  const authTimeout = setTimeout(() => {
    console.warn("Auth popup probably closed by user");
    isLoadingForAuth.value = false;
  }, 5000);

  tokenClient.requestAccessToken({ prompt: "" });
}

function openPicker(token: string) {
  gapi.load("picker", {
    callback: () => {
      const view = new google.picker.DocsView()
        .setIncludeFolders(true)
        .setMimeTypes("image/png,image/jpeg,image/jpg");

      const picker = new google.picker.PickerBuilder()
        .addView(view)
        .setOAuthToken(token)
        .setDeveloperKey(API_KEY)
        .setCallback(pickerCallback)
        .build();

      picker.setVisible(true);
    },
  });
}

async function pickerCallback(data: any) {
  if (data.action === google.picker.Action.PICKED) {
    selectedFile.value = data.docs[0];
    const fileId = selectedFile.value.id;

    const blob = await downloadFile(fileId, driveAuth.accessToken!);
    const previewUrl = URL.createObjectURL(blob);
    selectedImage.value = previewUrl;

    driveAuth.setLastFile(selectedFile.value);

    const name = selectedFile.value.name || "google-drive-image";
    const mime = blob.type && blob.type !== "" ? blob.type : "image/png";
    const file = new File([blob], name, { type: mime });

    pendingFile.value = file;

    if (props.cropper) {
      await nextTick();
      isCropperModalOpen.value = true;
    } else {
      croppedFile.value = file;
      customName.value = file.name.replace(/\.[^/.]+$/, "");
      currentView.value = "confirm";
    }
  }
}

async function downloadFile(fileId: string, token: string): Promise<Blob> {
  const res = await fetch(
    `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok)
    throw new Error(t("image-library.google-drive.errors.download-file"));
  return await res.blob();
}

onMounted(async () => {
  driveAuth.loadToken();
  driveAuth.loadLastFile();
});

async function useLastFile() {
  if (!driveAuth.lastFile) return;
  const fileId = driveAuth.lastFile.id;
  const blob = await downloadFile(fileId, driveAuth.accessToken!);
  const name = driveAuth.lastFile.name || "google-drive-image";
  const mime = blob.type && blob.type !== "" ? blob.type : "image/png";
  const file = new File([blob], name, { type: mime });
  pendingFile.value = file;

  if (props.cropper) {
    await nextTick();
    isCropperModalOpen.value = true;
  } else {
    croppedFile.value = file;
    customName.value = file.name.replace(/\.[^/.]+$/, "");
    currentView.value = "confirm";
  }
}

function handleSaveCrop(f: File) {
  isCropperModalOpen.value = false;
  pendingFile.value = null;
  croppedFile.value = f;
  customName.value = f.name.replace(/\.[^/.]+$/, "");
  currentView.value = "confirm";
}

async function confirmSelection() {
  if (!croppedFile.value) return;
  try {
    await object({
      customName: string()
        .trim()
        .required(t("image-library.common.image-name-required")),
    }).validate({ customName: customName.value });
    customNameError.value = "";
  } catch (err: any) {
    customNameError.value = err.message;
    return;
  }

  const dot = croppedFile.value.name.lastIndexOf(".");
  const name = customName.value?.trim() || croppedFile.value.name.slice(0, dot);
  const renamed = new File([croppedFile.value], name, {
    type: croppedFile.value.type,
  });

  const store = useImageLibraryStore();
  store.setSelectedFile(renamed, { cropped: true, source: "gdrive" });

  currentView.value = "picker";
  croppedFile.value = null;
}

function cancelConfirm() {
  currentView.value = "picker";
  croppedFile.value = null;
}
</script>

<template>
  <div class="tw:flex tw:flex-col tw:items-center tw:gap-6">
    <ModalImageCropper
      v-if="props.cropper && pendingFile"
      v-model="isCropperModalOpen"
      :imageFile="pendingFile"
      :aspectRatio="props.aspectRatio"
      @save="handleSaveCrop"
    />

    <div v-if="currentView === 'picker'" class="tw:w-full tw:text-center">
      <!-- Auth -->
      <div
        v-if="!selectedFile && !isLoadingForAuth && !driveAuth.accessToken"
        class="tw:flex tw:flex-col tw:items-center tw:gap-3 tw:bg-secondary/5 tw:px-6 tw:py-20"
      >
        <div class="tw:mb-1 tw:rounded-full tw:bg-primary/10 tw:p-8">
          <Icon
            icon="tabler-brand-google-drive"
            class="tw:text-5xl tw:text-primary/60"
          />
        </div>
        <p class="tw:text-xl">
          {{ $t("image-library.google-drive.link-your-account") }}
        </p>
        <Button size="md" @click="linkAccount" :uppercase="false">
          {{ $t("image-library.google-drive.link") }}
        </Button>
      </div>
      <!-- Loading -->
      <div
        v-else-if="isLoadingForAuth"
        class="tw:flex tw:items-center tw:justify-center tw:px-6 tw:py-10"
      >
        <Icon
          icon="tabler-loader-2"
          class="tw:animate-spin tw:text-3xl tw:text-primary"
        />
        <span class="tw:ml-2">
          {{ $t("image-library.google-drive.connecting-to-google") }}
        </span>
      </div>
      <!-- Connected -->
      <div v-else class="tw:p-6 tw:text-center">
        <p class="tw:text-lg">
          {{ $t("image-library.google-drive.last-image-selected") }}
        </p>
        <p class="tw:font-bold">
          {{
            selectedFile
              ? selectedFile.name
              : $t("image-library.google-drive.no-image-selected")
          }}
        </p>

        <div v-if="selectedImage" class="tw:mt-4">
          <img
            :src="selectedImage"
            class="tw:mx-auto tw:max-w-md tw:rounded-lg"
          />
        </div>

        <div class="tw:mt-6 tw:flex tw:justify-center tw:gap-4">
          <Button
            size="md"
            @click="linkAccount"
            :uppercase="false"
            variant="outlined"
          >
            {{ $t("image-library.google-drive.open-google-drive") }}
          </Button>

          <Button size="md" @click="useLastFile" :uppercase="false">
            {{ $t("image-library.google-drive.use-last-image") }}
          </Button>
        </div>
      </div>
    </div>

    <div
      v-else-if="currentView === 'confirm'"
      class="tw:flex tw:flex-col tw:items-center tw:gap-4 tw:p-6"
    >
      <h2 class="tw:text-xl tw:font-bold">
        {{ $t("image-library.common.confirm-image") }}
      </h2>

      <div class="tw:w-full tw:max-w-[420px]">
        <FieldText
          v-model="customName"
          name="custom_name"
          :label="$t('image-library.common.image-name')"
          :placeholder="$t('image-library.common.enter-image-name')"
          required
        />
        <p v-if="customNameError" class="tw:mt-1 tw:text-sm tw:text-error">
          {{ customNameError }}
        </p>
      </div>

      <div
        v-if="croppedFile"
        class="tw:w-full tw:max-w-[420px] tw:overflow-hidden tw:rounded-lg tw:border tw:border-secondary/20"
      >
        <img
          :src="previewUrl"
          :alt="$t('image-library.common.cropped-preview-alt')"
          class="tw:h-auto tw:w-full tw:object-cover"
        />
      </div>

      <div
        v-if="croppedFile"
        class="tw:text-center tw:text-sm tw:text-secondary"
      >
        <strong>{{ croppedFile.name }}</strong>
        <span class="tw:ml-1">
          ({{ Math.ceil(croppedFile.size / 1024) }} KB)
        </span>
      </div>

      <div class="tw:mt-4 tw:flex tw:gap-3">
        <Button color="primary" @click="confirmSelection">
          {{ $t("image-library.common.use-this-image") }}
        </Button>
        <Button variant="outlined" color="secondary" @click="cancelConfirm">
          {{ $t("image-library.common.change-image") }}
        </Button>
      </div>
    </div>
  </div>
</template>
