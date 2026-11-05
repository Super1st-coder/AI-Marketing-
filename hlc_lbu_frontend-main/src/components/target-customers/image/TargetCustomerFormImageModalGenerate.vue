<script lang="ts" setup>
import { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import { TargetCustomerFormData } from "../TargetCustomerForm.vue";
import { ProductData } from "@/services/ProductsApi";
import BuyerPersonImagesApi from "@/services/BuyerPersonImagesApi";

const props = defineProps<{
  products: ProductData[];
}>();

const isOpen = defineModel<boolean>({ required: true });
const emit = defineEmits<{ successAutomaticMode: []; selectManualMode: [] }>();
const { data } = useMultiStepFormContext<TargetCustomerFormData>();
const { t, te } = useI18n();

const screen = ref<"selection" | "product" | "loader">("selection");
const isReady = ref(false);
const generalErrorMessage = ref<string | undefined>(undefined);
const selectedProduct = ref<number | undefined>(
  props.products.find(
    (product) => product.id === data.value.product?.id && product.complete,
  )?.id,
);
const selectedVisualStyle = ref<ImageStudioVisualStyle | undefined>(undefined);
const areVisualStylesOpen = ref(false);
const createdVisualStyles = ref<ImageStudioVisualStyle[]>([]);

// Create an autocomplete list of options
const productOptions = computed<AutocompleteOption[]>(() =>
  [...props.products]
    .sort((a, b) => Number(b.complete) - Number(a.complete))
    .map((product) => ({
      value: product.id,
      label: product.name,
      image: product.thumbnail_url ?? undefined,
      disabled: !product.complete,
      chip: !product.complete
        ? {
            label: t("global.incomplete"),
            color: "error",
            variant: "label",
          }
        : undefined,
    })),
);

const generateLoaderSteps = computed(() => [
  t("buyer-person.image.generate-modal.loader.steps.analyzing"),
  t("buyer-person.image.generate-modal.loader.steps.setting-stage"),
  t("buyer-person.image.generate-modal.loader.steps.refining"),
  t("buyer-person.image.generate-modal.loader.steps.creating-variations"),
]);

function handleAutomaticMode() {
  screen.value = "product";
}

async function handleManualMode() {
  emit("selectManualMode");
}

function handleOpenVisualStyles() {
  areVisualStylesOpen.value = true;
}

function handleSelectVisualStyle(style: ImageStudioVisualStyle) {
  areVisualStylesOpen.value = false;
  selectedVisualStyle.value = style;
}

function handleRemoveVisualStyle() {
  selectedVisualStyle.value = undefined;
}

function handleCreateVisualStyle(style: ImageStudioVisualStyle) {
  createdVisualStyles.value = [...createdVisualStyles.value, style];
}

async function handleSkip() {
  selectedProduct.value = undefined;
  await handleGenerate();
}

async function handleGenerate() {
  generalErrorMessage.value = undefined;

  // Loader screen
  screen.value = "loader";

  try {
    const response = await BuyerPersonImagesApi.startGenerateMainImageListJob({
      brand_id: data.value.brandId,
      bperson_id: data.value.id,
      product_id: selectedProduct.value ?? null,
      visual_style: selectedVisualStyle.value?.name,
    });

    const jobId = response.data.job_id;

    // Start a pooling process to wait for the final response or error
    const result = await pooling(
      async () => {
        const { data: response } =
          await BuyerPersonImagesApi.getGenerateMainImageListJobResult(jobId);

        return response;
      },
      (response) => response.status === "DONE" || response.status === "FAILED",
      TARGET_CUSTOMER_IMAGE_JOB_POLLING_INTERVAL_MS,
      { timeoutMs: TARGET_CUSTOMER_IMAGE_MAIN_LIST_JOB_TIMEOUT_MS },
    );

    if (result.status === "FAILED") {
      // The job failed
      generalErrorMessage.value = t("global.unexpected-error");
      // Go back to the initial screen
      screen.value = "product";
      return;
    }

    // Display the last step in loader for a moment
    isReady.value = true;
    await sleep(4 * SECOND_IN_MS);

    // Emit success event
    emit("successAutomaticMode");
  } catch (error) {
    console.log(error);

    generalErrorMessage.value = t("global.unexpected-error");

    // Go back to the initial screen
    screen.value = "product";
  } finally {
  }
}
</script>

<template>
  <!-- Initial screen with selection -->
  <Modal
    v-if="screen === 'selection'"
    v-model="isOpen"
    :maxWidth="500"
    closeButton
    closeOnClickOutside
  >
    <ModalHeader>
      {{ $t("buyer-person.image.generate-modal.selection.title") }}

      <template #description>
        {{ $t("buyer-person.image.generate-modal.selection.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <div class="tw:grid tw:grid-cols-1 tw:gap-7">
        <CardButton icon="custom:hi-luca" @click="handleAutomaticMode">
          <template #title>
            {{
              $t("buyer-person.image.generate-modal.selection.automatic.title")
            }}
          </template>

          <template #description>
            {{
              $t(
                "buyer-person.image.generate-modal.selection.automatic.description",
              )
            }}
          </template>
        </CardButton>

        <CardButton icon="tabler:terminal" @click="handleManualMode">
          <template #title>
            {{ $t("buyer-person.image.generate-modal.selection.manual.title") }}
          </template>

          <template #description>
            {{
              $t(
                "buyer-person.image.generate-modal.selection.manual.description",
              )
            }}
          </template>
        </CardButton>
      </div>
    </ModalBody>
  </Modal>
  <!-- Screen with visual direction -->
  <Modal
    v-if="screen === 'product'"
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    closeOnClickOutside
    as="form"
    @submit.prevent="handleGenerate"
  >
    <ModalHeader>
      {{ $t("buyer-person.image.generate-modal.product.title") }}

      <template #description>
        {{ $t("buyer-person.image.generate-modal.product.description") }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-6">
      <FieldBaseControl
        :label="
          $t(
            'buyer-person.image.generate-modal.product.step-select-visual-style',
          )
        "
      >
        <div class="tw:flex">
          <ImageStudioChip
            v-if="selectedVisualStyle"
            :src="selectedVisualStyle.image ?? selectedVisualStyle.image_url"
            @click="handleRemoveVisualStyle"
            @clickImage="handleOpenVisualStyles"
          >
            {{
              te(`image-studio.visual-styles.${selectedVisualStyle.name}.title`)
                ? t(
                    `image-studio.visual-styles.${selectedVisualStyle.name}.title`,
                  )
                : selectedVisualStyle.name
            }}
          </ImageStudioChip>
          <Button
            v-else
            type="button"
            color="secondary"
            variant="outlined"
            leftIcon="tabler:plus"
            @click="handleOpenVisualStyles"
          >
            {{
              $t("buyer-person.image.generate-modal.product.add-visual-style")
            }}
          </Button>
        </div>
      </FieldBaseControl>

      <FieldBaseAutocomplete
        v-model="selectedProduct"
        :label="
          $t('buyer-person.image.generate-modal.product.step-link-product')
        "
        :options="productOptions"
        leftIcon="tabler:search"
        :placeholder="
          $t('buyer-person.image.generate-modal.product.search-placeholder')
        "
        clearable
      />

      <Alert v-if="generalErrorMessage" type="error">
        {{ generalErrorMessage }}
      </Alert>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        color="secondary"
        variant="outlined"
        @click="handleSkip"
      >
        {{ $t("global.skip") }}
      </Button>

      <Button
        type="submit"
        :disabled="!selectedVisualStyle && selectedProduct === undefined"
      >
        {{ $t("buyer-person.image.generate-modal.product.generate-image") }}
      </Button>
    </ModalFooter>

    <ImageStudioVisualStylesModal
      v-if="areVisualStylesOpen"
      v-model="areVisualStylesOpen"
      :customStyles="createdVisualStyles"
      :initialSelected="selectedVisualStyle"
      @select="handleSelectVisualStyle"
      @create="handleCreateVisualStyle"
    />
  </Modal>
  <!-- Ring loader -->
  <ModalRingLoader
    v-else-if="screen === 'loader'"
    v-model="isOpen"
    :isReady="isReady"
    :interval="TARGET_CUSTOMER_IMAGE_RING_LOADER_INTERVAL_MS"
    :steps="generateLoaderSteps"
  >
    <template #title>
      {{ $t("buyer-person.image.generate-modal.loader.title") }}
    </template>
    <template #description>
      {{ $t("buyer-person.image.generate-modal.loader.description") }}
    </template>
  </ModalRingLoader>
</template>
