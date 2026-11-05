<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { TargetCustomerFormData } from "./TargetCustomerForm.vue";
import { getSummaryRefinerCategories } from "../forms/category-refiner/categoryRefinerTypes";
import BuyerPersonasApi from "@/services/BuyerPersonasApi";
import BuyerPersonImagesApi from "@/services/BuyerPersonImagesApi";
import { targetCustomerRefinerStyles } from "@/constants/target-customers";

const { t } = useI18n();
const brandId = useBrandId();
const router = useRouter();
const { targetProjectRoute } = useProjectQueryShorcut();

const { data, goBack, goToStep } =
  useMultiStepFormContext<TargetCustomerFormData>();

const mandatoryCategories = getSummaryRefinerCategories(
  data.value.mandatory_attributes_saved,
  data.value.mandatory_attributes_generated,
);

async function getSummaryImages() {
  try {
    const { main_images } = (
      await BuyerPersonImagesApi.getMainImageList(brandId, data.value.id)
    ).data;

    const selectedMainImage = main_images.find((image) => image.selected);

    if (selectedMainImage) {
      const { variants } = (
        await BuyerPersonImagesApi.getMainImageVariants(
          brandId,
          data.value.id,
          selectedMainImage.image_id,
        )
      ).data;

      return [
        selectedMainImage.image_url,
        ...variants.map((variant) => variant.image_url),
      ];
    }
  } catch {
    // Legacy image flow or API error — fall back to stored thumbnail
  }

  return data.value.thumbnail_url ? [data.value.thumbnail_url] : [];
}

const images = await getSummaryImages();

const schema = computed(() =>
  toTypedSchema(
    object({
      bperson_story: string().required(t("forms.required-field")).trim(),
      nickname: string().trim(),
    }),
  ),
);

const namebuyer = computed(
  () => data.value.mandatory_attributes_saved?.name_and_nickname[0] ?? "",
);

const { handleSubmit, isSubmitting, values, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    bperson_story: data.value.bperson_story ?? undefined,
    nickname: namebuyer.value,
  },
});

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  const bperson_id = data.value.id;

  if (!data.value.locked) {
    // Update buyer person story
    await BuyerPersonasApi.completeBuyerPerson(
      brandId,
      bperson_id,
      values.bperson_story,
      values.nickname ?? data.value.name,
    );
  }

  // Disable the save alert
  disableSaveAlert.value = true;

  // Navigate to the brand
  if (targetProjectRoute.value) {
    // Navigate to the project
    router.replace(targetProjectRoute.value);
  } else {
    // Navigate to the buyer person list
    router.push({ name: "BuyerPersonList" });
  }
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :maxWidth="1130">
    <div class="tw:flex tw:flex-col tw:gap-5 tw:lg:flex-row tw:lg:items-start">
      <CardBase
        class="tw:shrink-0 tw:grow tw:md:top-[66px] tw:lg:sticky tw:lg:order-last tw:lg:max-w-[331px]"
      >
        <div class="tw:p-4">
          <ImageSlider v-if="images.length" :images="images" />
        </div>

        <template v-if="!data.locked">
          <Separator />

          <div class="tw:p-4">
            <Button
              class="tw:w-full"
              size="sm"
              color="secondary"
              variant="outlined"
              leftIcon="tabler:pencil"
              type="button"
              @click="goToStep(2)"
            >
              {{ $t("buyer-person.summary.edit-image") }}
            </Button>
          </div>
        </template>
      </CardBase>

      <div class="tw:grid tw:grow tw:grid-cols-1 tw:gap-10">
        <CardBase>
          <div class="tw:p-6">
            <div class="tw:flex tw:items-start tw:gap-5">
              <FieldEditableText
                name="nickname"
                required
                class="tw:text-4xl tw:font-bold"
                variant="text"
                :editable="!data.locked"
                :disabled="data.locked || isSubmitting"
              />

              <ButtonVideoHelp
                src="https://www.youtube.com/watch?v=4fM3Rz1ey1E"
              >
                {{ values.nickname ?? data.name }}
              </ButtonVideoHelp>
            </div>
          </div>

          <Separator />

          <div class="tw:p-6">
            <EditableCardSection
              name="bperson_story"
              :title="$t('buyer-person.summary.story')"
              icon="tabler:file-description"
              :editable="!data.locked"
              class="tw:w-full"
              :disabled="data.locked || isSubmitting"
            />
          </div>
        </CardBase>

        <div class="tw:grid tw:grow tw:grid-cols-1 tw:gap-6">
          <CategoryRefinerSummary
            :categories="mandatoryCategories"
            :styles="targetCustomerRefinerStyles"
            @edit="goToStep(1)"
            :editable="!data.locked"
          >
            <template #title>{{ $t("refiner.mandatory-categories") }}</template>
          </CategoryRefinerSummary>
        </div>
      </div>
    </div>

    <template #actions>
      <WizardCardActions>
        <PermissionGuard
          :requires="[{ name: 'TARGET_CUSTOMER', actions: ['U'] }]"
        >
          <ButtonGoBack @click="goBack" />
          <ButtonNext :isLoading="isSubmitting">
            {{
              data.locked
                ? $t("buyer-person.summary.back-to-target-customers")
                : $t("global.save")
            }}
          </ButtonNext>
        </PermissionGuard>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
