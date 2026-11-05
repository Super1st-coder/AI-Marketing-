<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { number, object } from "yup";
import { FunnelPaidSocialFormData } from "../FunnelPaidSocialForm.vue";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";

defineProps<{
  campaignName: string;
}>();

const brandId = useBrandId();
const campaignId = useCampaignId();
const paidSocialFormStore = useFunnelPaidSocialFormStore();

const isOpen = defineModel<boolean>({ required: true });

const { data, goNext } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      numberOfAdSets: number().required(),
      adsPerAdSet: number().required(),
    }),
  ),
);

const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    numberOfAdSets: 1,
    adsPerAdSet: 2,
  },
  keepValuesOnUnmount: true,
});

const onSubmit = handleSubmit(async (values) => {
  // Create the ad structure
  await AdStructureApi.defineAdStructure(
    brandId,
    campaignId,
    data.value.channelGroupId,
    {
      ad_set_number: values.numberOfAdSets,
      ad_number: values.adsPerAdSet,
    },
  );

  // Revalidate funnel flow
  await paidSocialFormStore.revalidate();

  goNext();
});
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.structure.create-modal.title") }}

      <template #description>
        {{
          $t("funnel-flow.paid-social.structure.create-modal.description", {
            campaignName,
          })
        }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldSelect
          name="numberOfAdSets"
          :label="
            $t(
              'funnel-flow.paid-social.structure.create-modal.fields.number-of-ad-sets',
            )
          "
          :options="[
            { label: '1', value: 1 },
            { label: '2', value: 2 },
            { label: '3', value: 3 },
            { label: '4', value: 4 },
            { label: '5', value: 5 },
            { label: '6', value: 6 },
          ]"
        />
        <FieldSelect
          name="adsPerAdSet"
          :label="
            $t(
              'funnel-flow.paid-social.structure.create-modal.fields.ads-per-ad-set',
            )
          "
          :options="[
            { label: '1', value: 1 },
            { label: '2', value: 2 },
            { label: '3', value: 3 },
            { label: '4', value: 4 },
            { label: '5', value: 5 },
            { label: '6', value: 6 },
          ]"
        />
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        variant="outlined"
        :disabled="isSubmitting"
        @click="close"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button type="submit" :isLoading="isSubmitting">
        {{
          $t(
            "funnel-flow.paid-social.structure.create-modal.actions.create-structure",
          )
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
