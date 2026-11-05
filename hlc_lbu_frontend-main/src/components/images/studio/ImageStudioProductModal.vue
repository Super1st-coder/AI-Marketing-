<script lang="ts" setup>
import { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import ProductsApi, { ProductData } from "@/services/ProductsApi";

const props = defineProps<{ brandId: number; initialProductId?: number }>();
const emit = defineEmits<{ select: [product: ProductData] }>();
const { t } = useI18n();

const isOpen = defineModel<boolean>({ required: true });

const allProducts = ref<ProductData[]>([]);
const isLoading = ref(false);
const selectedProduct = ref<number | undefined>(undefined);

// Fetch all products of the brand
async function fetchProducts() {
  isLoading.value = true;

  allProducts.value = await fetchAllItems((range) =>
    ProductsApi.getList(props.brandId, {
      range,
      order: { updatedAt: "desc" },
    }),
  );

  isLoading.value = false;
}

// Create an autocomplete list of options
const productOptions = computed<AutocompleteOption[]>(() =>
  [...allProducts.value]
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

function handleAddProduct() {
  const product = allProducts.value.find(
    (product) => product.id === selectedProduct.value && product.complete,
  );

  if (product) {
    emit("select", product);
    isOpen.value = false;
  }
}

onMounted(async () => {
  await fetchProducts();
  if (props.initialProductId) {
    const product = allProducts.value.find(
      (item) => item.id === props.initialProductId && item.complete,
    );
    if (product) {
      selectedProduct.value = product.id;
    }
  }
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="500"
    closeButton
    closeOnClickOutside
    v-slot="{ close }"
    as="form"
    @submit.prevent="handleAddProduct"
  >
    <ModalHeader>
      {{ $t("image-studio.product-modal.title") }}

      <template #description>
        {{ $t("image-studio.product-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldBaseAutocomplete
        v-model="selectedProduct"
        :options="productOptions"
        leftIcon="tabler:search"
        :placeholder="$t('image-studio.product-modal.search-placeholder')"
        clearable
        :loading="isLoading"
      />
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" type="button" @click="close">
        {{ $t("global.cancel") }}
      </Button>

      <Button @click="handleAddProduct" :disabled="!selectedProduct">
        {{ $t("image-studio.product-modal.add-product") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
