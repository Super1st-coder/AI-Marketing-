<script lang="ts" setup>
const props = defineProps<{
  label?: string;
}>();

const emit = defineEmits<{
  addFile: [image: ImageLibraryFile, label?: string];
  generateWithLuca: [label: string];
  writeToLuca: [];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const imageLibraryStore = useImageLibraryStore();
const libraryTargetId = ref(Symbol("ImageLibraryModal"));

const screen = ref<"selection" | "library" | "scanning" | "mismatch">(
  "selection",
);
const selectedFile = ref<ImageLibraryFile | undefined>(undefined);

const translatedLabel = computed(() =>
  props.label ? t(`buyer-person.image.variations.${props.label}.title`) : "",
);

const scanningTexts = computed(() => [
  t("buyer-person.image.variation-add-modal.scanning.one"),
  t("buyer-person.image.variation-add-modal.scanning.two"),
  t("buyer-person.image.variation-add-modal.scanning.three"),
]);

function handleUploadFile() {
  imageLibraryStore.setActiveTarget(libraryTargetId.value);
  screen.value = "library";
}

function handleFileUploaded(file: ImageLibraryFile) {
  emit("addFile", file, props.label);
  isOpen.value = false;
}

async function handleScan(file: ImageLibraryFile) {
  selectedFile.value = file;
  screen.value = "scanning";

  // TODO: call real endpoint to scan
  await sleep(5 * SECOND_IN_MS);
  const mismatchDetected = Math.random() > 0.99999;

  if (mismatchDetected) {
    screen.value = "mismatch";
  } else {
    handleFileUploaded(file);
  }
}

// Store the selected image from the library
watch(
  () => imageLibraryStore.selectedFile,
  async (file) => {
    if (!file) return;

    if (
      imageLibraryStore.lastTarget &&
      imageLibraryStore.lastTarget === libraryTargetId.value
    ) {
      if (props.label && TARGET_CUSTOMER_IMAGE_VARIATION_ANALYZE_ENABLED) {
        await handleScan(file);
      } else {
        handleFileUploaded(file);
      }
    }
  },
);

function handleTryAnotherImage() {
  selectedFile.value = undefined;
  screen.value = "library";
}

function handleGenerateWithLuca() {
  if (props.label) {
    emit("generateWithLuca", props.label);
    isOpen.value = false;
  }
}

function handleWriteToLuca() {
  emit("writeToLuca");
  isOpen.value = false;
}
</script>

<template>
  <Modal
    v-if="screen === 'selection'"
    v-model="isOpen"
    :maxWidth="500"
    closeButton
    closeOnClickOutside
  >
    <ModalHeader>
      <template v-if="label">
        {{
          $t("buyer-person.image.variation-add-modal.label-required", {
            label: translatedLabel,
          })
        }}
      </template>
      <template v-else>
        {{ $t("buyer-person.image.variation-add-modal.how-to-add") }}
      </template>

      <template #description>
        <template v-if="label">
          {{ $t("buyer-person.image.variation-add-modal.label-description") }}
        </template>
        <template v-else>
          {{
            $t("buyer-person.image.variation-add-modal.how-to-add-description")
          }}
        </template>
      </template>
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-7">
      <template v-if="label">
        <!-- TODO: add functionality -->
        <CardButton icon="custom:hi-luca" @click="handleGenerateWithLuca">
          <template #title>
            {{
              $t(
                "buyer-person.image.variation-add-modal.generate-automatic.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "buyer-person.image.variation-add-modal.generate-automatic.description",
              )
            }}
          </template>
        </CardButton>

        <CardButton icon="tabler:upload" @click="handleUploadFile">
          <template #title>
            {{ $t("buyer-person.image.variation-add-modal.upload-file.title") }}
          </template>

          <template #description>
            {{
              $t(
                "buyer-person.image.variation-add-modal.upload-file.description-label",
              )
            }}
          </template>
        </CardButton>
      </template>
      <template v-else>
        <!-- TODO: add functionality -->
        <CardButton icon="tabler:terminal" @click="handleWriteToLuca">
          <template #title>
            {{
              $t("buyer-person.image.variation-add-modal.write-to-luca.title")
            }}
          </template>

          <template #description>
            {{
              $t(
                "buyer-person.image.variation-add-modal.write-to-luca.description",
              )
            }}
          </template>
        </CardButton>

        <CardButton icon="tabler:upload" @click="handleUploadFile">
          <template #title>
            {{ $t("buyer-person.image.variation-add-modal.upload-file.title") }}
          </template>

          <template #description>
            {{
              $t(
                "buyer-person.image.variation-add-modal.upload-file.description",
              )
            }}
          </template>
        </CardButton>
      </template>
    </ModalBody>
  </Modal>
  <!-- Image Library Modal -->
  <ImageLibraryModal
    v-else-if="screen === 'library'"
    v-model="isOpen"
    cropper
  />
  <!-- Modal to display while scanning image -->
  <Modal
    v-else-if="screen === 'scanning'"
    v-model="isOpen"
    fallbackFocusToForeground
    :maxWidth="500"
    :closeOnClickOutside="false"
    class="tw:p-6"
  >
    <CardBase
      color="secondary"
      class="tw:mx-auto tw:flex tw:aspect-square tw:items-center tw:justify-center"
      style="max-width: 300px"
    >
      <CyclingText :texts="scanningTexts" :interval="0.5 * SECOND_IN_MS" />
    </CardBase>
  </Modal>
  <!-- Image mismatch warning -->
  <Modal
    v-else-if="screen === 'mismatch'"
    v-model="isOpen"
    :maxWidth="500"
    closeButton
    closeOnClickOutside
  >
    <ModalHeader> </ModalHeader>
    <ModalBody>
      <ImgFile
        :src="selectedFile"
        class="tw:mx-auto tw:mb-6 tw:rounded-2xl tw:object-contain"
        style="max-height: 300px"
      />

      <Alert type="warning">
        <template #title>
          {{ $t("buyer-person.image.variation-add-modal.mismatch.title") }}
        </template>

        {{ $t("buyer-person.image.variation-add-modal.mismatch.description") }}
      </Alert>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        leftIcon="tabler:upload"
        variant="label"
        color="primary"
        @click="handleTryAnotherImage"
      >
        {{ $t("buyer-person.image.variation-add-modal.mismatch.try-another") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
