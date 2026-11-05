<template>
  <TopNav />

  <GenericSubLayout belowNavbar>
    <!-- ── Topbar: back arrow ── -->
    <template #headerBackAction>
      <RouterLink :to="{ name: 'BrandList' }">
        <Icon icon="tabler-arrow-left" class="tw:text-2xl" />
      </RouterLink>
    </template>

    <!-- ── Topbar: left — title ── -->
    <template #headerLeft>
      <h2 class="tw:pl-3 tw:font-medium tw:text-primary-text">
        Design Transformation
      </h2>
    </template>

    <!-- ── Topbar: right — badge ── -->
    <template #headerRight>
      <ChipList> </ChipList>
    </template>

    <!-- ── Page content ── -->
    <Container :maxWidth="1090" class="tw:py-10">
      <div class="tw:flex tw:flex-col tw:gap-6">
        <!-- ── Tenant Account Card ── -->
        <CardBase class="tw:p-6">
          <h2 class="tw:mb-4 tw:font-semibold tw:text-primary-text">
            Tenant Account
          </h2>

          <div class="tw:flex tw:items-end tw:gap-3">
            <div class="tw:min-w-0 tw:grow">
              <FieldText
                v-model="accountId"
                name="account-id"
                label="Account ID"
                placeholder="e.g. 123"
                @keyup.enter="fetchFiles"
              />
            </div>

            <Button
              left-icon="tabler-refresh"
              :isLoading="loadingFiles"
              :disabled="!accountId || loadingFiles"
              class="tw:mb-[2px]"
              @click="fetchFiles"
            >
              List Files
            </Button>
          </div>
        </CardBase>

        <!-- ── Main Sections ── -->
        <AccordionList variant="card">
          <!-- ─ Upload Section ─ -->
          <Accordion>
            <template #title>
              <strong>Upload File</strong>
            </template>

            <div class="tw:flex tw:max-w-lg tw:flex-col tw:gap-5">
              <!-- File picker -->
              <div class="tw:flex tw:flex-col tw:gap-1.5">
                <FieldLabel for="file-upload-input">Select file</FieldLabel>
                <input
                  ref="fileInputRef"
                  id="file-upload-input"
                  type="file"
                  class="tw:bg-gray-50 tw:block tw:w-full tw:cursor-pointer tw:rounded-xl tw:border tw:border-gray-300 tw:text-sm tw:text-secondary-text tw:transition tw:file:mr-4 tw:file:cursor-pointer tw:file:rounded-l-xl tw:file:border-0 tw:file:bg-primary-100 tw:file:px-4 tw:file:py-2.5 tw:file:text-sm tw:file:font-semibold tw:file:text-primary tw:hover:file:bg-primary-200 tw:focus:outline-hidden"
                  @change="onFileSelected"
                />
              </div>

              <!-- File info preview -->
              <CardBase
                v-if="selectedFile"
                color="secondary"
                :shadow="false"
                class="tw:p-4"
              >
                <div class="tw:flex tw:flex-col tw:gap-1.5 tw:text-sm">
                  <div class="tw:flex tw:gap-2">
                    <span
                      class="tw:w-16 tw:shrink-0 tw:font-semibold tw:text-primary-text"
                      >Name</span
                    >
                    <span
                      class="tw:min-w-0 tw:truncate tw:text-secondary-text"
                      >{{ selectedFile.name }}</span
                    >
                  </div>
                  <div class="tw:flex tw:gap-2">
                    <span
                      class="tw:w-16 tw:shrink-0 tw:font-semibold tw:text-primary-text"
                      >Size</span
                    >
                    <span class="tw:text-secondary-text">{{
                      formatBytes(selectedFile.size)
                    }}</span>
                  </div>
                  <div class="tw:flex tw:gap-2">
                    <span
                      class="tw:w-16 tw:shrink-0 tw:font-semibold tw:text-primary-text"
                      >Type</span
                    >
                    <span class="tw:text-secondary-text">{{
                      selectedFile.type || "application/octet-stream"
                    }}</span>
                  </div>
                </div>
              </CardBase>

              <!-- Upload button -->
              <div>
                <Button
                  left-icon="tabler-cloud-upload"
                  :isLoading="loadingUpload"
                  :disabled="loadingUpload || !selectedFile || !accountId"
                  @click="uploadFile"
                >
                  Upload to GCS
                </Button>
              </div>

              <!-- Progress bar -->
              <div
                v-if="uploadProgress !== null"
                class="tw:flex tw:flex-col tw:gap-2"
              >
                <div class="tw:flex tw:justify-between tw:text-sm">
                  <span class="tw:font-medium tw:text-primary-text"
                    >Upload progress</span
                  >
                  <span class="tw:font-semibold tw:text-primary"
                    >{{ uploadProgress }}%</span
                  >
                </div>
                <div
                  class="tw:h-2 tw:w-full tw:overflow-hidden tw:rounded-full tw:bg-gray-200"
                >
                  <div
                    class="tw:h-2 tw:rounded-full tw:bg-primary tw:transition-all tw:duration-200"
                    :style="{ width: `${uploadProgress}%` }"
                  />
                </div>
              </div>

              <!-- Upload success -->
              <Alert v-if="uploadSuccess" type="success">
                File uploaded successfully!
              </Alert>

              <!-- Upload error -->
              <Alert v-if="errorUpload" type="error">
                <pre class="tw:text-sm tw:whitespace-pre-wrap">{{
                  errorUpload
                }}</pre>
              </Alert>
            </div>
          </Accordion>

          <!-- ─ Files Section ─ -->
          <Accordion openByDefault>
            <template #title>
              <strong>
                Files
                <span
                  v-if="fileList.length"
                  class="tw:ml-2 tw:text-sm tw:font-normal tw:text-secondary-text"
                >
                  ({{ fileList.length }})
                </span>
              </strong>
            </template>

            <!-- Error -->
            <Alert v-if="errorFiles" type="error" class="tw:mb-4">
              {{ errorFiles }}
            </Alert>

            <!-- File rows -->
            <div v-if="fileList.length > 0" class="tw:flex tw:flex-col">
              <!-- Table head -->
              <div
                class="tw:grid tw:gap-4 tw:border-b tw:border-gray-200 tw:pb-3 tw:text-xs tw:font-semibold tw:tracking-wider tw:text-secondary-text tw:uppercase"
                style="grid-template-columns: 2fr 90px 1fr 1fr auto"
              >
                <span>Filename</span>
                <span>Size</span>
                <span>Content Type</span>
                <span>Updated</span>
                <span>Actions</span>
              </div>

              <!-- Rows -->
              <template v-for="(file, index) in fileList" :key="file.blob_name">
                <div
                  class="tw:grid tw:items-center tw:gap-4 tw:py-3"
                  style="grid-template-columns: 2fr 90px 1fr 1fr auto"
                >
                  <span
                    class="tw:truncate tw:font-medium tw:text-primary-text"
                    :title="file.filename"
                  >
                    {{ file.filename }}
                  </span>

                  <span class="tw:text-sm tw:text-secondary-text">
                    {{ formatBytes(file.size) }}
                  </span>

                  <span class="tw:truncate tw:text-sm tw:text-secondary-text">
                    {{ file.content_type }}
                  </span>

                  <span class="tw:text-sm tw:text-secondary-text">
                    {{ formatDate(file.updated) }}
                  </span>

                  <div class="tw:flex tw:gap-2">
                    <Button
                      variant="outlined"
                      color="secondary"
                      size="sm"
                      left-icon="tabler-download"
                      :isLoading="downloadingFile === file.filename"
                      :disabled="!!downloadingFile || !!resizingPsd"
                      @click="downloadFile(file.filename)"
                    >
                      Download
                    </Button>

                    <!-- PSD Resize button — only for .psd files -->
                    <Button
                      v-if="file.filename.toLowerCase().endsWith('.psd')"
                      variant="outlined"
                      color="primary"
                      size="sm"
                      left-icon="tabler-layers-intersect"
                      :isLoading="resizingPsd === file.filename"
                      :disabled="!!resizingPsd || !!downloadingFile"
                      @click="resizePsd(file.filename)"
                    >
                      Resize PSD
                    </Button>

                    <Button
                      variant="outlined"
                      color="error"
                      size="sm"
                      left-icon="tabler-trash"
                      :isLoading="deletingFile === file.filename"
                      :disabled="!!deletingFile"
                      @click="confirmDeleteFile(file.filename)"
                    >
                      Delete
                    </Button>
                  </div>
                </div>

                <Separator v-if="index < fileList.length - 1" />
              </template>
            </div>

            <!-- Empty — fetched but nothing -->
            <div
              v-else-if="!loadingFiles && filesFetched"
              class="tw:flex tw:flex-col tw:items-center tw:gap-3 tw:py-10 tw:text-center"
            >
              <Icon
                icon="tabler:file-off"
                class="tw:text-5xl tw:text-gray-300"
              />
              <p class="tw:text-sm tw:text-secondary-text">
                No files found for this account.
              </p>
            </div>

            <!-- Idle — not yet searched -->
            <div
              v-else-if="!loadingFiles && !filesFetched"
              class="tw:flex tw:flex-col tw:items-center tw:gap-3 tw:py-10 tw:text-center"
            >
              <Icon
                icon="tabler:cloud-search"
                class="tw:text-5xl tw:text-gray-300"
              />
              <p class="tw:text-sm tw:text-secondary-text">
                Enter an Account ID above and click <strong>List Files</strong>.
              </p>
            </div>
          </Accordion>
        </AccordionList>
      </div>
    </Container>

    <!-- ── Delete confirmation modal ── -->
    <Modal v-model="showDeleteModal" closeButton>
      <ModalHeader>Delete file</ModalHeader>

      <ModalBody>
        <p class="tw:text-secondary-text">
          Are you sure you want to delete
          <strong class="tw:text-primary-text">{{ fileToDelete }}</strong
          >? This action cannot be undone.
        </p>
      </ModalBody>

      <ModalFooter>
        <Button
          variant="outlined"
          color="secondary"
          @click="showDeleteModal = false"
        >
          Cancel
        </Button>

        <Button
          color="error"
          :isLoading="!!deletingFile"
          left-icon="tabler-trash"
          @click="executeDelete"
        >
          Delete
        </Button>
      </ModalFooter>
    </Modal>
  </GenericSubLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";
import StorageApi, { StorageFile } from "@/services/tests/StorageApi";

// ─── State ────────────────────────────────────────────────────────────────────

const notificationStore = useNotificationStore();

const accountId = ref("");

// Files
const fileList = ref<StorageFile[]>([]);
const loadingFiles = ref(false);
const errorFiles = ref("");
const filesFetched = ref(false);

// Upload
const fileInputRef = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const loadingUpload = ref(false);
const uploadProgress = ref<number | null>(null);
const uploadSuccess = ref(false);
const errorUpload = ref("");

// Download
const downloadingFile = ref<string | null>(null);

// PSD Resize
const resizingPsd = ref<string | null>(null);

// Delete
const deletingFile = ref<string | null>(null);
const fileToDelete = ref<string | null>(null);
const showDeleteModal = ref(false);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleString();
  } catch (e: unknown) {
    console.error(e);
    return dateStr;
  }
}

// ─── Actions ──────────────────────────────────────────────────────────────────

const fetchFiles = async () => {
  if (!accountId.value) return;

  loadingFiles.value = true;
  errorFiles.value = "";
  fileList.value = [];

  try {
    const response = await StorageApi.listFiles(accountId.value);
    fileList.value = response.data ?? [];
  } catch (err: any) {
    const detail = err.data || err.response?._data || err.message;
    errorFiles.value =
      typeof detail === "object"
        ? JSON.stringify(detail, null, 2)
        : String(detail || "Failed to list files");
  } finally {
    loadingFiles.value = false;
    filesFetched.value = true;
  }
};

const onFileSelected = (event: Event) => {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
  uploadProgress.value = null;
  uploadSuccess.value = false;
  errorUpload.value = "";
};

const uploadFile = async () => {
  if (!selectedFile.value || !accountId.value) return;

  loadingUpload.value = true;
  uploadProgress.value = 0;
  uploadSuccess.value = false;
  errorUpload.value = "";

  try {
    const { data: urlData } = await StorageApi.getUploadUrl(accountId.value, {
      filename: selectedFile.value.name,
      content_type: selectedFile.value.type || "application/octet-stream",
    });

    await StorageApi.uploadToGcs(
      urlData.upload_url,
      selectedFile.value,
      (percent) => {
        uploadProgress.value = percent;
      },
    );

    uploadSuccess.value = true;
    uploadProgress.value = 100;

    notificationStore.display({
      type: "success",
      title: "File uploaded",
      description: `"${selectedFile.value.name}" was uploaded successfully.`,
    });

    selectedFile.value = null;
    if (fileInputRef.value) fileInputRef.value.value = "";

    await fetchFiles();
  } catch (err: any) {
    const detail = err.data || err.response?._data || err.message;
    errorUpload.value =
      typeof detail === "object"
        ? JSON.stringify(detail, null, 2)
        : String(detail || "Upload failed");
    uploadProgress.value = null;
  } finally {
    loadingUpload.value = false;
  }
};

const downloadFile = async (filename: string) => {
  downloadingFile.value = filename;
  try {
    const blobUrl = await StorageApi.downloadFile(accountId.value, filename);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000);
  } catch (err: any) {
    const detail = err.data || err.response?._data || err.message;
    notificationStore.display({
      type: "error",
      title: "Download failed",
      description:
        typeof detail === "object"
          ? JSON.stringify(detail)
          : String(detail || "Unknown error"),
    });
  } finally {
    downloadingFile.value = null;
  }
};

// ── PSD Resize ────────────────────────────────────────────────────────────────
const resizePsd = async (filename: string) => {
  resizingPsd.value = filename;
  try {
    // Step 1: Send account_id and filename directly to Sinergia
    // Sinergia will download the PSD from Google Storage internally and stream it to Cloud Run.
    const form = new FormData();
    form.append("account_id", accountId.value);
    form.append("filename", filename);
    form.append("preserve_layers", "true");
    form.append("engine", "auto");
    form.append("auto_layout", "false");

    const zipBlob = await $api<Blob>("/v2/psd-resize", {
      method: "POST",
      body: form,
      responseType: "blob" as any,
      timeout: 300_000, // 5 min
    });

    // Step 3: trigger download
    const zipUrl = URL.createObjectURL(zipBlob);
    const a = document.createElement("a");
    a.href = zipUrl;
    a.download = `${filename.replace(/\.psd$/i, "")}_exports.zip`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(zipUrl), 10_000);

    notificationStore.display({
      type: "success",
      title: "PSD processed",
      description: `"${filename}" was resized and downloaded as a ZIP.`,
    });
  } catch (err: any) {
    const detail =
      err?.message?.text || err?.message || err?.data || "Unknown error";
    notificationStore.display({
      type: "error",
      title: "PSD Resize failed",
      description:
        typeof detail === "object" ? JSON.stringify(detail) : String(detail),
    });
  } finally {
    resizingPsd.value = null;
  }
};

const confirmDeleteFile = (filename: string) => {
  fileToDelete.value = filename;
  showDeleteModal.value = true;
};

const executeDelete = async () => {
  if (!fileToDelete.value) return;

  const filename = fileToDelete.value;
  deletingFile.value = filename;

  try {
    await StorageApi.deleteFile(accountId.value, filename);
    showDeleteModal.value = false;

    notificationStore.display({
      type: "success",
      title: "File deleted",
      description: `"${filename}" was deleted successfully.`,
    });

    await fetchFiles();
  } catch (err: any) {
    const detail = err.data || err.response?._data || err.message;
    notificationStore.display({
      type: "error",
      title: "Delete failed",
      description:
        typeof detail === "object"
          ? JSON.stringify(detail)
          : String(detail || "Unknown error"),
    });
  } finally {
    deletingFile.value = null;
    fileToDelete.value = null;
  }
};
</script>
