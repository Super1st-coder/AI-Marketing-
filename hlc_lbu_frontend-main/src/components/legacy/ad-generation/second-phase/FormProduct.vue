<script lang="ts" setup>
import { array, object } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { Product, productSchema } from "./cards/LegacyProductCard.vue";
import SecondPhaseProduct, {
  ProductData,
} from "@/services/legacy/SecondPhaseProduct";
import SecondPhaseHypothesis from "@/services/legacy/SecondPhaseHypothesis";
import { UnidentifiedError } from "@/services/common-errors";

const store = useAdGenerationStore();
const projectId = store.projectId;

if (!store.data.products) {
  throw new UnidentifiedError();
}

// Map the person buyers
const initialValues = store.data.products?.map<Product>((product) => {
  return {
    id: product.Product.id,
    selected: product.Product.preferred === 1,
    title: product.Product.Name,
    coreCharacteristic: product.Product.Details.Core_Characteristic,
    advantage: product.Product.Details.Competitive_Advantage,
    description: product.Product.Details.Description,
    benefit: product.Product.Details.Benefit_Related_to_Hypothesis,
    details: product.Product.Details.Product_Details.Features,
  };
});

const image = await SecondPhaseProduct.getImage(projectId, true);
if (image) {
  const selectedProduct = initialValues.find((product) => product.selected);
  if (selectedProduct) {
    selectedProduct.file = image;
  }
}

const { handleSubmit, setFieldValue, values, errors, submitCount } =
  useFormWithErrorScrolling({
    initialValues: {
      products: initialValues,
    },
    validationSchema: toTypedSchema(
      object().shape({
        products: array()
          .of(productSchema)
          .required()
          .test((items) => {
            return items.some((item) => item.selected);
          })
          .test("need-file", "You need to upload an image file.", (items) => {
            // See if the selected item has a file
            const selectedItem = items.find((item) => item.selected);
            //console.log(selectedItem);

            return selectedItem?.file;
          }),
      }),
    ),
    keepValuesOnUnmount: true,
  });

const selectedProduct = computed(() =>
  values.products?.find((item) => item.selected),
);

const isLoading = ref(false);

const onSubmit = handleSubmit(async (values) => {
  if (!selectedProduct.value) {
    throw new UnidentifiedError();
  }

  isLoading.value = true;

  // Save data locally
  const products = values.products.map<ProductData>((product) => ({
    Product: {
      id: product.id,
      Name: product.title,
      Type: `Product ${Number(product.id) + 1}`,
      preferred: product.selected ? 1 : 0,
      Details: {
        Description: product.description,
        Product_Details: {
          Features: product.details,
        },
        Core_Characteristic: product.coreCharacteristic,
        Competitive_Advantage: product.advantage,
        Benefit_Related_to_Hypothesis: product.benefit,
      },
    },
  }));
  store.data.products = products;
  store.data.preferred_product = products.find(
    (product) => product.Product.preferred === 1,
  );

  // Save all products. We sort the array to move the selected product to the end
  const sortedProducts = [...products].sort((a, b) =>
    a.Product.preferred > b.Product.preferred ? 1 : -1,
  );
  for (const product of sortedProducts) {
    // Set as preferred first, because the save endpoint doesn't accept an id, it saves the
    // preferred product
    await SecondPhaseProduct.setPreferred(projectId, product.Product.id);

    // Save the product
    await SecondPhaseProduct.savePreferred(projectId, product);
  }

  // Upload image
  await SecondPhaseProduct.uploadImage(projectId, selectedProduct.value.file);

  // Get the dropdown options for the next step
  await SecondPhaseHypothesis.getBuilderElements(projectId);
  store.data.hypothesis_builder_preferred_option = undefined;

  // Go to next step
  store.goNext();
});

const handleChecked = (checked: boolean, value: Product) => {
  const index = values.products?.findIndex((item) => item.id === value.id);

  if (checked) {
    // Uncheck all except this one
    values.products?.forEach((_, _index) => {
      if (index != _index) {
        setFieldValue(`products.${_index}.selected`, false);
      }
    });
  }
};

const areCardsExpanded = ref(false);

// Keep the height of cards
useMaxHeightCards(
  [
    ".card-header",
    ".card-title-and-paragraph",
    ".card-advantage",
    ".card-description",
    ".card-benefit",
    ".card-details",
  ],
  [values, areCardsExpanded],
);
</script>

<template>
  <form
    @submit="onSubmit"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        {{ $t("process.product.title") }}
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        {{ $t("process.product.description") }}
      </WizardCardParagraph>
    </div>

    <CardGrid>
      <LegacyProductCard
        v-for="(_, index) in values.products"
        :name="`products[${index}]`"
        @checked="handleChecked"
        v-model:expanded="areCardsExpanded"
        class="tw:grow tw:basis-0"
      />
    </CardGrid>

    <Alert v-if="errors.products && submitCount > 0" type="error">
      {{ errors.products }}
    </Alert>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :disabled="!selectedProduct" :isLoading="isLoading" />
    </WizardCardActions>
  </form>
</template>
