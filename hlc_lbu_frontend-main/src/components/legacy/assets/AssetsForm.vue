<script setup lang="ts">
import { AssetTemplate } from "@/services/legacy/AssetsApi";
import CampaignsApi from "@/services/projects/CampaignsApi";

export type AssetsFormData = {
  projectId?: string;
  currentTemplateId?: string;
  currentTemplate?: AssetTemplate;
  currentImageIndex?: number;
};

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const { data } = await CampaignsApi.getOne(brandId, projectId, campaignId);

const steps = computed<FormStep[]>(() => [
  {
    name: "setup",
    label: t("campaigns.assets.sidebarmenu.setuptitle"),
    icon: "tabler:template",
  },
  {
    name: "builder",
    label: t("campaigns.assets.sidebarmenu.buildertitle"),
    icon: "tabler:ruler-2",
  },
  {
    name: "delivery",
    label: t("campaigns.assets.sidebarmenu.deliverytitle"),
    icon: "tabler:truck-delivery",
  },
]);

const savedSelectedTemplate = useLocalStorage<string | undefined>(
  `brands.${brandId}.assets.${campaignId}.currentTemplate`,
  undefined,
);

const savedStep = useLocalStorage<number>(
  `brands.${brandId}.assets.${campaignId}.currentStep`,
  0,
);

// Initialize the multi-step form
const { currentFlatStepIndex } = useMultiStepForm<AssetsFormData>(steps, {
  useLocalStorage: true,
  blockForwardNavigation: true,
  initialData: {
    projectId: data.asset_platform_project_id ?? undefined,
    currentTemplateId: savedSelectedTemplate.value,
  },
  initialStep:
    savedSelectedTemplate.value && savedStep.value ? savedStep.value : 0,
  id: (_data) => `assets-${campaignId}`,
});

watch(currentFlatStepIndex, (value) => {
  savedStep.value = value;
});
</script>

<template>
  <MultiStepForm>
    <template #sidebarHeader>
      <SidebarTitle variant="secondary" size="sm">
        {{ $t("campaigns.assets.sidebarmenu.title") }}
      </SidebarTitle>

      <SidebarTitle>
        {{ data.name }}
      </SidebarTitle>
    </template>

    <FormStep name="setup">
      <AssetsFormSetup />
    </FormStep>

    <FormStep name="builder">
      <AssetsFormBuilder />
    </FormStep>

    <FormStep name="delivery">
      <AssetsFormDelivery />
    </FormStep>

    <template #sidebarFooter>
      <SidebarLink
        :to="{ name: 'CampaignSettings' }"
        variant="link"
        icon="tabler-arrow-left"
      >
        {{ $t("campaigns.assets.backto", { name: data.name }) }}
      </SidebarLink>
    </template>
  </MultiStepForm>
</template>
