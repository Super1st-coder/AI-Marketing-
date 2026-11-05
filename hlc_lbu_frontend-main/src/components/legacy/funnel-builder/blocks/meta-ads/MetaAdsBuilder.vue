<script lang="ts" setup>
import { array, object } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRoute, useRouter } from "vue-router";
import {
  MetaAd,
  metaAdSchema,
} from "@/components/legacy/funnel-builder/blocks/meta-ads/MetaAdCard.vue";
import MetaAdsAPI, { MetaAdType } from "@/services/legacy/MetaAdsAPI";
import ProjectsAPI from "@/services/legacy/ProjectsAPI";

const props = defineProps<{ type: MetaAdType }>();

const router = useRouter();
const route = useRoute();
const store = useFunnelBuilderStore();

// Fetch the project
const projectId = parseInt(route.params.id as string);
const project = await ProjectsAPI.getOne(projectId);

// Fetch the initial ads data
let response = await MetaAdsAPI.getList(projectId, props.type);
if (response.data.meta_ads.length === 0) {
  response = await MetaAdsAPI.generate(projectId, props.type);
}

// Load images
const adImages = await Promise.all(
  response.data.meta_ads.map((ad) =>
    MetaAdsAPI.getImage(projectId, props.type, ad.id, true),
  ),
);

// Format the data for the form
const initialAds: MetaAd[] = response.data.meta_ads.map((ad, adIndex) => {
  const selectedPrompt = ad.image_prompts?.prompts?.find(
    (prompt) => prompt.preferred === 1,
  );

  return {
    id: ad.id,
    selected: ad.preferred === 1,
    title: `Ad copy ${adIndex + 1}`,
    context: ad.context,
    primaryText: ad.ad.primary_text,
    imageHook: ad.ad.image_hook,
    imagePunchline: ad.ad.image_punchline,
    headline: ad.ad.headline,
    description: ad.ad.description,
    cta: ad.ad.cta,
    imageGeneration: ad.image_prompts?.prompts
      ? {
          prompts: ad.image_prompts.prompts.map((item) => item.description),
          selectedPromptIndex: selectedPrompt?.id,
          selectedPrompt: selectedPrompt?.description,
          generatedImage: adImages[adIndex],
        }
      : undefined,
  };
});

const {
  handleSubmit,
  setFieldValue,
  values,
  errors,
  submitCount,
  isFieldDirty,
} = useFormWithErrorScrolling({
  initialValues: {
    metaAds: store.data.metaAds ?? initialAds,
  },
  validationSchema: toTypedSchema(
    object().shape({
      metaAds: array()
        .of(metaAdSchema)
        .required()
        .test("select", "You need to select one ad.", (items) => {
          return items.some((item) => item.selected);
        })
        .test(
          "need-image",
          "You have to generate an image in the selected ad.",
          (items) => {
            const selected = items.find((item) => item.selected);
            return !!selected?.imageGeneration?.generatedImage;
          },
        ),
    }),
  ),
  keepValuesOnUnmount: true,
});

const handleChecked = (checked: boolean, value: MetaAd) => {
  const index = values.metaAds?.findIndex((item) => item.id === value.id);

  if (checked) {
    // Uncheck all except this one
    values.metaAds?.forEach((_, _index) => {
      if (index != _index) {
        setFieldValue(`metaAds.${_index}.selected`, false);
      }
    });
  }
};

const handleGeneratePrompts = async (index: number) => {
  // Set loading
  setFieldValue(`metaAds.${index}.imageGeneration`, { isLoading: true });

  // Fetch the prompts
  const response = await MetaAdsAPI.generatePrompts(
    projectId,
    props.type,
    index,
  );

  // Save the prompts
  setFieldValue(`metaAds.${index}.imageGeneration`, {
    prompts: flattenPrompts(
      response.data.target_meta_ad.image_prompts?.prompts,
    ),
  });
};

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save all the ads
  for (const [index, ad] of values.metaAds.entries()) {
    if (isFieldDirty(`metaAds.${index}`)) {
      await MetaAdsAPI.saveOne(projectId, props.type, {
        id: ad.id,
        preferred: ad.selected ? 1 : 0,
        context: ad.context,
        ad: {
          cta: ad.cta,
          headline: ad.headline,
          image_hook: ad.imageHook,
          image_punchline: ad.imagePunchline,
          primary_text: ad.primaryText,
          description: ad.description,
        },
        image_prompts: ad.imageGeneration?.prompts
          ? {
              prompts: ad.imageGeneration?.prompts.map((prompt, index) => ({
                id: index,
                description: prompt,
                preferred:
                  index === ad.imageGeneration?.selectedPromptIndex ? 1 : 0,
              })),
            }
          : undefined,
      });
    }
  }

  // Upload the images
  for (const [index, ad] of values.metaAds.entries()) {
    if (
      ad.imageGeneration?.generatedImage &&
      isFieldDirty(`metaAds.${index}`) &&
      ad.imageGeneration.generatedImage instanceof Blob
    ) {
      await MetaAdsAPI.uploadImage(
        projectId,
        props.type,
        ad.id,
        ad.imageGeneration.generatedImage,
      );
    }
  }

  // Go to the building blocks
  router.push({ name: "PaidSocial" });
});
//#endregion
</script>

<template>
  <WizardCard paddingY="lg">
    <form
      @submit="onSubmit"
      class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
    >
      <div>
        <WizardCardTitle>
          Meta ads Builder
          <template #button>
            <HelpButton> Help info </HelpButton>
          </template>
        </WizardCardTitle>

        <WizardCardParagraph>
          Generate 3 that are aligned with your experiment before moving
          forward. 3 is Meta-recommended for each selected audience.
        </WizardCardParagraph>
      </div>

      <CardGrid class="tw:content-start tw:items-start">
        <MetaAdCard
          v-for="(item, index) in values.metaAds"
          :projectId="projectId"
          :name="`metaAds[${index}]`"
          @checked="(checked) => handleChecked(checked, item)"
          :brandName="project.data.brand_name ?? 'unknown'"
          @generatePrompts="handleGeneratePrompts(index)"
        />
      </CardGrid>

      <Alert v-if="errors.metaAds && submitCount > 0" type="error">
        {{ errors.metaAds }}
      </Alert>

      <WizardCardActions>
        <WizardButtonGoBack @click="router.push({ name: 'PaidSocial' })" />

        <WizardButtonNext :isLoading="isLoading">
          SAVE AD COPIES
        </WizardButtonNext>
      </WizardCardActions>
    </form>
  </WizardCard>
</template>
