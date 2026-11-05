<script setup lang="ts">
import { FunnelPaidSocialFormData } from "./FunnelPaidSocialForm.vue";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import AudienceApi from "@/services/projects/AudienceApi";
import CampaignsApi from "@/services/projects/CampaignsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";
import AdsExperiment from "@/services/funnel-flow/paid-social/AdsExperiment";
import AdsApi, {
  AdChannelDefinition,
  AdMediaFormat,
  getChannelSelectedVariant,
} from "@/services/funnel-flow/paid-social/AdsApi";
import ProductsApi, { ProductData } from "@/services/ProductsApi";
import { getSummaryRefinerCategories } from "@/components/forms/category-refiner/categoryRefinerTypes";
import BuyerPersonasApi, { BuyerPersonData } from "@/services/BuyerPersonasApi";
import { targetCustomerRefinerStyles } from "@/constants/target-customers";
import { productRefinerStyles } from "@/components/products/productContants";

const { data, goBack, goNext } =
  useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();

const modalFormats = ref(false);
const formats = ref<AdMediaFormat[]>([]);
const adsetNameRef = ref("");
const adNameRef = ref("");

const buyerPersonModal = ref(false);
const productModal = ref(false);
const campaignModal = ref(false);
const umbrellaCampaignModal = ref(false);

// Fetch ad structure
const [{ data: project }, { data: campaign }, { data: adStructure }] =
  await Promise.all([
    ProjectsApi.getOne(brandId, projectId),
    CampaignsApi.getOne(brandId, projectId, campaignId),
    AdStructureApi.getAdStructureByChannelGroup(
      brandId,
      campaignId,
      data.value.channelGroupId,
    ),
  ]);

const { data: umbrellaCampaign } = await UmbrellaCampaignsApi.getOne(
  brandId,
  projectId,
  campaign.ucampaign?.id,
);

// Fetch the audiences of all sets
const audiences = await Promise.all(
  adStructure.ad_sets.map(
    async (set) =>
      (await AudienceApi.GetAudiencesByAdSet(brandId, campaignId, set.id)).data
        .audiences,
  ),
);

// Fetch the experiments
const experiments = await Promise.all(
  adStructure.ad_sets.map(
    async (set) =>
      (await AdsExperiment.getExperimentByAdSet(brandId, campaignId, set.id))
        .data,
  ),
);

// Fetch the ads
const ads = await Promise.all(
  adStructure.ad_sets.map(
    async (set) =>
      await Promise.all(
        set.ads.map(
          async (ad) =>
            (await AdsApi.getOneAd(brandId, campaignId, ad.id)).data,
        ),
      ),
  ),
);

const joinedData = computed(() =>
  adStructure.ad_sets.map((set, index) => ({
    ...set,
    audiences: audiences[index],
    experiment: experiments[index],
    ads: ads[index],
  })),
);

function getChannel(
  channel: AdChannelDefinition,
  adSetName: string,
  adName: string,
) {
  modalFormats.value = true;
  formats.value = getChannelSelectedVariant(channel)!.media.formats!;
  adsetNameRef.value = adSetName;
  adNameRef.value = adName;
}

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
</script>

<template>
  <FormStepLayout>
    <div class="tw:pt-6">
      <PageTitle is="h2">
        {{
          $t("funnel-flow.paid-social.summary.page-title.title", {
            name: campaign.name,
          })
        }}

        <template #description>
          {{ $t("funnel-flow.paid-social.summary.page-title.description") }}
        </template>
      </PageTitle>
    </div>

    <Separator class="tw:py-0" />

    <div class="tw:flex tw:flex-col tw:gap-7 tw:pb-7">
      <div
        class="tw:flex tw:items-center tw:gap-2 tw:rounded-xl tw:border tw:border-primary/24 tw:bg-primary/8 tw:p-4"
      >
        <Icon
          icon="tabler-circle-check-filled"
          class="tw:text-2xl tw:text-success"
        />
        <p>
          {{ $t("funnel-flow.paid-social.summary.success-banner.description") }}
        </p>
      </div>

      <AccordionList>
        <Accordion
          :title="
            $t('funnel-flow.paid-social.summary.accordion.full-details-title')
          "
          variant="text"
        >
          <div class="tw:grid tw:gap-4 tw:lg:grid-cols-4">
            <FunnelPaidSocialFormSummaryCard
              @click="buyerPersonModal = true"
              :imgSrc="project.bperson?.thumbnail_url"
            >
              <template #title>
                {{
                  $t(
                    "funnel-flow.paid-social.summary.cards.target-customer.title",
                  )
                }}
              </template>

              <template #description>
                {{ project.bperson?.bperson_story }}
              </template>
            </FunnelPaidSocialFormSummaryCard>

            <FunnelPaidSocialFormSummaryCard
              @click="productModal = true"
              :imgSrc="project.product?.thumbnail_url"
            >
              <template #title>
                {{ $t("funnel-flow.paid-social.summary.cards.product.title") }}
              </template>

              <template #description>
                {{ project.product?.product_story }}
              </template>
            </FunnelPaidSocialFormSummaryCard>

            <FunnelPaidSocialFormSummaryCard
              @click="umbrellaCampaignModal = true"
              :imgSrc="umbrellaCampaign.thumbnail_url"
            >
              <template #title>
                {{
                  $t(
                    "funnel-flow.paid-social.summary.cards.umbrella-campaign.title",
                  )
                }}
              </template>

              <template #description>
                {{ umbrellaCampaign.benefit_reasoning }}
              </template>
            </FunnelPaidSocialFormSummaryCard>

            <FunnelPaidSocialFormSummaryCard
              @click="campaignModal = true"
              :imgSrc="campaign.thumbnail_url"
            >
              <template #title>
                {{ $t("funnel-flow.paid-social.summary.cards.campaign.title") }}
              </template>

              <template #description>
                {{ campaign.description }}
              </template>
            </FunnelPaidSocialFormSummaryCard>
          </div>
        </Accordion>
      </AccordionList>

      <AdsetsSummary :joinedData="joinedData" @get-channel="getChannel" />
    </div>

    <AdFormatsPreviewModal
      v-model="modalFormats"
      :adSetName="adsetNameRef"
      :adName="adNameRef"
      :formats="formats"
    />

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
        {{ $t("global.campaign") }}
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

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />

        <Button @click="goNext">
          {{ $t("funnel-flow.paid-social.summary.actions.send-to-design") }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
