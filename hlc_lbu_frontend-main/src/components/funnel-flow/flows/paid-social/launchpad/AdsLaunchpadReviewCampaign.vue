<script setup lang="ts">
import BuyerPersonasApi, { BuyerPersonData } from "@/services/BuyerPersonasApi";
import ProductsApi, { ProductData } from "@/services/ProductsApi";
import CampaignsApi from "@/services/projects/CampaignsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";
import { getSummaryRefinerCategories } from "@/components/forms/category-refiner/categoryRefinerTypes";
import { targetCustomerRefinerStyles } from "@/constants/target-customers";
import { productRefinerStyles } from "@/components/products/productContants";

const { goNext, goBack } = useMultiStepFormContext();

const brandId = useBrandId();
const campaignId = useCampaignId();
const projectId = useProjectId();
const buyerPersonModal = ref(false);
const productModal = ref(false);
const campaignModal = ref(false);
const umbrellaCampaignModal = ref(false);
const strategyDetailsModal = ref(false);

const { data: campaign } = await CampaignsApi.getOne(
  brandId,
  projectId,
  campaignId,
);

const { data: umbrellaCampaign } = await UmbrellaCampaignsApi.getOne(
  brandId,
  projectId,
  campaign.ucampaign?.id,
);

const { data: project } = await ProjectsApi.getOne(brandId, projectId);

let product: ProductData;
let optionalCategories;
let mandatoryProductCategories;
if (project.product?.id != null) {
  const { data } = await ProductsApi.getOne(brandId, project.product.id);
  product = data;

  optionalCategories = getSummaryRefinerCategories(
    product.optional_attributes_saved,
    product.optional_attributes_generated,
  );

  mandatoryProductCategories = getSummaryRefinerCategories(
    product.mandatory_attributes_saved,
    product.mandatory_attributes_generated,
  );
}

let buyerPerson: BuyerPersonData;
let mandatoryCategories;
if (project.bperson?.id != null) {
  const { data } = await BuyerPersonasApi.getOne(brandId, project.bperson?.id);
  buyerPerson = data;

  mandatoryCategories = getSummaryRefinerCategories(
    buyerPerson.mandatory_attributes_saved,
    buyerPerson.mandatory_attributes_generated,
  );
}

const categories = [...mandatoryProductCategories, ...optionalCategories];

function goBackMediaPlan() {
  goBack();
}
</script>

<template>
  <FormStepLayout>
    <!-- Horizontal Stepper -->
    <template #stepper>
      <AdsLaunchpadStepper />
    </template>

    <!-- Title Section -->
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=PS-LLZhhrJA"
    >
      {{ $t("funnel-flow.paid-social.launchpad.review-campaign.title") }}
      <template #description>
        {{
          $t("funnel-flow.paid-social.launchpad.review-campaign.description")
        }}
      </template>
    </PageTitle>

    <!-- Campaign Summary Card with Expandable Content -->
    <AdsLaunchpadCampaignHeader :campaign="campaign">
      <AdsLaunchpadCampaignHeaderReviewCampaign :campaign="campaign" />
    </AdsLaunchpadCampaignHeader>

    <!-- Info Cards - Reordered: Campaign, Target Customer, Product, Umbrella Campaign -->
    <div class="tw:mt-6 tw:grid tw:grid-cols-4 tw:gap-4">
      <CardBase
        is="button"
        type="button"
        @click="campaignModal = true"
        class="tw:flex tw:flex-col tw:gap-3 tw:p-4 tw:text-sm"
      >
        <h4 class="tw:truncate tw:text-base tw:font-bold">
          {{ $t("global.campaigns") }}
        </h4>

        <img
          v-if="campaign.thumbnail_url"
          class="tw:rounded-xl"
          :src="campaign.thumbnail_url"
          alt=""
        />

        <span class="tw:tp-5 tw:line-clamp-6 tw:text-secondary">
          {{ campaign.description }}
        </span>
      </CardBase>

      <CardBase
        is="button"
        type="button"
        @click="buyerPersonModal = true"
        class="tw:flex tw:flex-col tw:gap-3 tw:p-4 tw:text-sm"
      >
        <h4 class="tw:truncate tw:text-base tw:font-bold">
          {{ $t("global.target-customer") }}
        </h4>

        <img
          v-if="buyerPerson.thumbnail_url"
          class="tw:rounded-xl"
          :src="buyerPerson.thumbnail_url"
          alt=""
        />

        <span class="tw:line-clamp-6 tw:text-secondary">
          {{ buyerPerson.bperson_story }}
        </span>
      </CardBase>

      <CardBase
        is="button"
        type="button"
        @click="productModal = true"
        class="tw:flex tw:flex-col tw:gap-3 tw:p-4 tw:text-sm"
      >
        <h4 class="tw:truncate tw:text-base tw:font-bold">
          {{ $t("global.product") }}
        </h4>

        <img
          v-if="product.thumbnail_url"
          class="tw:rounded-xl"
          :src="product.thumbnail_url"
          alt=""
        />

        <span class="tw:line-clamp-6 tw:text-secondary">
          {{ product.product_story }}
        </span>
      </CardBase>

      <CardBase
        is="button"
        type="button"
        @click="umbrellaCampaignModal = true"
        class="tw:flex tw:flex-col tw:gap-3 tw:p-4 tw:text-sm"
      >
        <h4 class="tw:truncate tw:text-base tw:font-bold">
          {{ $t("global.umbrella-campaign") }}
        </h4>

        <img
          v-if="umbrellaCampaign.thumbnail_url"
          class="tw:rounded-xl"
          :src="umbrellaCampaign.thumbnail_url"
          alt=""
        />

        <span class="tw:line-clamp-6 tw:text-secondary">
          {{ umbrellaCampaign.benefit_reasoning }}
        </span>
      </CardBase>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBackMediaPlan" />
        <Button
          icon="tabler-arrow-narrow-right"
          @click="
            () => {
              goNext();
            }
          "
        >
          {{
            $t(
              "funnel-flow.paid-social.launchpad.review-campaign.proceed-to-structure",
            )
          }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>

  <ProjectFormSelectionModal
    v-model="buyerPersonModal"
    :completed="buyerPerson.complete"
    :name="buyerPerson.name"
    :description="buyerPerson.bperson_story"
    :categories="mandatoryCategories"
    :categoriesStyles="targetCustomerRefinerStyles"
    :images="buyerPerson.thumbnail_url ? [buyerPerson.thumbnail_url] : []"
    :withActions="false"
    :editRoute="{}"
  />

  <ProjectFormSelectionModal
    v-model="productModal"
    :completed="product.complete"
    :name="product.name"
    :description="product.product_story || product.description"
    :categories="categories"
    :categoriesStyles="productRefinerStyles"
    :images="
      product.images?.map((image) => image.url) ??
      (product.thumbnail_url ? [product.thumbnail_url] : [])
    "
    :withActions="false"
    :editRoute="{}"
  />

  <Modal
    :modelValue="campaignModal"
    @update:modelValue="
      () => {
        campaignModal = false;
      }
    "
    class="tw:p-10"
    :maxWidth="1024"
    closeButton
  >
    <h2 class="tw:mb-5 tw:text-4xl tw:font-extrabold">
      {{ $t("global.campaigns") }}
    </h2>
    <CampaignFormSummaryCard
      :bpersonName="buyerPerson.name"
      :productName="product.name"
      :campaign="campaign"
    />
  </Modal>

  <Modal
    :modelValue="umbrellaCampaignModal"
    @update:modelValue="
      () => {
        umbrellaCampaignModal = false;
      }
    "
    class="tw:p-10"
    :maxWidth="1024"
    closeButton
  >
    <h2 class="tw:mb-5 tw:text-4xl tw:font-extrabold">
      {{ $t("global.umbrella-campaign") }}
    </h2>
    <UmbrellaCampaignFormSummaryCards :umbrellaCampaign="umbrellaCampaign" />
  </Modal>

  <!-- Strategy Details Modal -->
  <Modal
    :modelValue="strategyDetailsModal"
    @update:modelValue="
      () => {
        strategyDetailsModal = false;
      }
    "
    class="tw:p-10"
    :maxWidth="640"
    closeButton
  >
    <h2 class="tw:mb-2 tw:text-2xl tw:font-bold">
      {{
        $t(
          "funnel-flow.paid-social.launchpad.common.campaign-strategic-details",
        )
      }}
    </h2>
    <p class="tw:mb-6 tw:text-secondary">
      {{
        $t(
          "funnel-flow.paid-social.launchpad.common.campaign-strategic-details-description",
        )
      }}
    </p>

    <CardBase class="tw:p-5">
      <!-- Funnel Stage & Geographic Targeting -->
      <div class="tw:flex tw:items-center tw:justify-between tw:py-3">
        <span class="tw:font-semibold">
          {{
            $t("funnel-flow.paid-social.launchpad.common.funnel-stage-strategy")
          }}
        </span>
        <span class="tw:text-secondary">{{ campaign.funnel?.name }}</span>
      </div>
      <div
        class="tw:flex tw:items-center tw:justify-between tw:border-b tw:border-gray-200 tw:py-3"
      >
        <span class="tw:font-semibold">
          {{
            $t("funnel-flow.paid-social.launchpad.common.geographic-targeting")
          }}
        </span>
        <span class="tw:text-secondary">{{ campaign.target_regions }}</span>
      </div>

      <!-- Creative Concept & Narrative -->
      <div class="tw:py-4">
        <h4 class="tw:mb-2 tw:font-semibold">
          {{
            $t(
              "funnel-flow.paid-social.launchpad.common.creative-concept-narrative",
            )
          }}
        </h4>
        <p class="tw:text-secondary">{{ campaign.description }}</p>
      </div>

      <div class="tw:border-t tw:border-gray-200 tw:pt-4">
        <h4 class="tw:mb-6 tw:font-semibold">
          {{ $t("funnel-flow.paid-social.launchpad.common.user-journey-path") }}
        </h4>
        <div class="tw:space-y-5">
          <div class="tw:flex tw:gap-3">
            <div
              class="tw:mt-1.5 tw:h-2 tw:w-2 tw:shrink-0 tw:rounded-full tw:bg-primary/60"
            />
            <div>
              <p class="tw:font-medium">
                {{ campaign.preferred_campaign?.sections?.funnel_flow?.title }}
              </p>
              <p
                class="tw:mt-2 tw:leading-relaxed tw:whitespace-pre-line tw:text-secondary"
              >
                {{ campaign.preferred_campaign?.sections?.funnel_flow?.text }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </CardBase>
  </Modal>
</template>
