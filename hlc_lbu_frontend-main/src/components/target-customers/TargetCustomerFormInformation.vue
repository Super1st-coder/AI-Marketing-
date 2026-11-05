<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, number, object, string } from "yup";
import { TargetCustomerFormData } from "./TargetCustomerForm.vue";
import ProductsAPI from "@/services/ProductsApi";
import BuyerPersonasApi, {
  BuyerPersonCreateResponse,
} from "@/services/BuyerPersonasApi";
import { appLocalesArray } from "@/plugins/i18n";
import { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";

const { locale, t } = useI18n();
const route = useRoute();
const router = useRouter();

const brandId = useBrandId();
const fetchedProducts = await fetchAllItems((range) =>
  ProductsAPI.getList(brandId, {
    range,
    order: { updatedAt: "desc" },
  }),
);

const productsOptions = computed<AutocompleteOption[]>(() =>
  [...fetchedProducts]
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

const { data, saveData, goNext, setDirtyStage } = useMultiStepFormContext<
  TargetCustomerFormData | undefined
>();

const { confirm } = useConfirmModal();
const { confirm: confirmSuggestion } = useConfirmModal(
  "targetCustomerSuggestions",
);

const schema = computed(() =>
  toTypedSchema(
    object({
      language: string().required(t("forms.required-field")),
      name: string().required(t("forms.required-field")).trim(),
      description_01: string().required(t("forms.required-field")).trim(),
      description_02: string().required(t("forms.required-field")).trim(),
      description_03: string().required(t("forms.required-field")).trim(),
      product_id: number().nullable(),
      files: array().of(mixed<File>().required(t("forms.required-field"))),
    }),
  ),
);

const { handleSubmit, meta, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    language:
      data.value?.language ??
      appLocalesArray.find((appLocale) => locale.value === appLocale.code)
        ?.apiName,
    name: data.value?.name ?? undefined,
    description_01: data.value?.description_01,
    description_02: data.value?.description_02,
    description_03: data.value?.description_03,
    product_id: data.value?.product?.id ?? null,
    files: data.value?.files,
  },
});

const disableSaveAlert = ref(false);
const generalErrorMessage = ref<string>();

const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;
  // Skip if it's locked
  if (data.value?.locked) {
    goNext({ isDirty: false });
    return;
  }

  // Display suggestion
  if (!values.product_id || !values.files || values.files.length === 0) {
    const result = await confirmSuggestion();
    if (result === "cancel") {
      return;
    }
  }

  let triggerGeneration = true;

  // Display and wait for the confirm modal if needed
  if (data.value?.mandatory_attributes_generated) {
    if (meta.value.dirty) {
      // Display the modal if the data is dirty
      const result = await confirm();
      if (result === "close") {
        return;
      }

      triggerGeneration = result === "continue";
    } else {
      // If the data is not dirty, do not trigger prompts
      triggerGeneration = false;
    }
  }

  let createUpdateResponse: BuyerPersonCreateResponse;
  if (data.value?.id) {
    // Update existing brand
    createUpdateResponse = await BuyerPersonasApi.update(
      brandId,
      data.value.id,
      {
        name: values.name,
        language: values.language,
        description_01: values.description_01,
        description_02: values.description_02,
        description_03: values.description_03,
      },
    );
  } else {
    // Create Buyer Person and save data
    createUpdateResponse = await BuyerPersonasApi.create(brandId, values);
  }

  const buyerPersonId = createUpdateResponse.data.id;

  // Set the product id
  const responseBuyer = await BuyerPersonasApi.setProduct(
    brandId,
    buyerPersonId,
    values.product_id ?? null,
  );
  const setProduct = fetchedProducts.find(
    (product) => product.id === values.product_id,
  );

  // Upload files
  if (values.files && values.files.length > 0) {
    const resp = await BuyerPersonasApi.uploadFiles(
      brandId,
      buyerPersonId,
      values.files,
    );

    if (String(resp.message?.code) === "UPLDOC00") {
      generalErrorMessage.value = t(
        `buyer-person.information.files.errormessage`,
      );
      saveData({
        ...createUpdateResponse.data,
        ...responseBuyer.data,
        product: setProduct ? { ...setProduct } : null,
        files: values.files,
      });

      return;
    }
  }

  // Generate attributes
  const attributesResponse = await BuyerPersonasApi.generateAttributes(
    brandId,
    buyerPersonId,
    triggerGeneration,
  );

  // Set stage as dirty
  if (meta.value.dirty) {
    setDirtyStage("image", true);
    setDirtyStage("summary", true);
  }

  if (data.value?.id) {
    // Go to the next step
    saveData({
      ...createUpdateResponse.data,
      ...attributesResponse.data,
      product: setProduct ? { ...setProduct } : null,
      files: values.files,
    });
    goNext({ isDirty: meta.value.dirty });
  } else {
    // Go to the settings page
    disableSaveAlert.value = true;
    await router.replace({
      name: "BuyerPersonSettings",
      params: { buyerPersonId: createUpdateResponse.data.id },
      query: route.query,
      hash: route.hash,
    });
  }
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=wzsdpyJ2Eok"
    >
      {{ $t("buyer-person.information.title") }}
    </PageTitle>

    <FieldsContainer>
      <FieldLanguage
        name="language"
        :label="$t('buyer-person.information.language.label')"
        :placeholder="$t('buyer-person.information.language.placeholder')"
        orientation="horizontal"
        required
        :disabled="data?.locked || isSubmitting"
      />

      <FieldTextarea
        name="name"
        :label="$t('buyer-person.information.name.label')"
        :placeholder="$t('buyer-person.information.name.placeholder')"
        orientation="horizontal"
        required
        speechRecognition
        :rows="1"
        :disabled="data?.locked || isSubmitting"
      />

      <FieldTextarea
        name="description_01"
        :label="$t('buyer-person.information.description_01.label')"
        :placeholder="$t('buyer-person.information.description_01.placeholder')"
        orientation="horizontal"
        required
        speechRecognition
        :rows="1"
        :disabled="data?.locked || isSubmitting"
      />

      <FieldTextarea
        name="description_02"
        :label="$t('buyer-person.information.description_02.label')"
        :placeholder="$t('buyer-person.information.description_02.placeholder')"
        orientation="horizontal"
        required
        speechRecognition
        :rows="1"
        :disabled="data?.locked || isSubmitting"
      />

      <FieldTextarea
        name="description_03"
        :label="$t('buyer-person.information.description_03.label')"
        :placeholder="$t('buyer-person.information.description_03.placeholder')"
        orientation="horizontal"
        required
        speechRecognition
        :rows="1"
        :disabled="data?.locked || isSubmitting"
      />

      <FieldAutocomplete
        name="product_id"
        :label="$t('buyer-person.information.product_id.label')"
        orientation="horizontal"
        :options="productsOptions"
        leftIcon="tabler:search"
        :placeholder="
          $t('buyer-person.information.product_id.search-placeholder')
        "
        clearable
        :disabled="data?.locked || isSubmitting"
      />

      <FieldFiles
        name="files"
        :label="$t('buyer-person.information.files.label')"
        :dropAreaLabel="$t('buyer-person.information.files.input-title')"
        :disabled="data?.locked || isSubmitting"
      />
    </FieldsContainer>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack :to="{ name: 'BuyerPersonList' }" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalConfirmRegeneration />

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />

    <ModalConfirmSuggestions name="targetCustomerSuggestions">
      <template #title>
        {{ $t("buyer-person.information.recommendation-modal.title") }}
      </template>

      <template #description>
        {{ $t("buyer-person.information.recommendation-modal.description") }}
      </template>
    </ModalConfirmSuggestions>
  </FormStepLayout>
</template>
