<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import AdStructureApi, {
  AdSetData,
} from "@/services/funnel-flow/paid-social/AdStructureApi";

const { t } = useI18n();

const brandId = useBrandId();
const campaignId = useCampaignId();

const props = defineProps<{
  channelGroupId: number;
  adStructureId: number;
  adSet: AdSetData;
}>();

const emit = defineEmits<{
  saved: [payload: { id: number; name: string }];
}>();

const isOpen = defineModel<boolean>({ required: true });

const generalErrorMessage = ref<string | null>(null);

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string()
        .required(t("forms.required-field"))
        .trim()
        .max(META_ADS_MAX_NAME_LENGTH, ({ max }) =>
          t("forms.max-characters", { max }),
        ),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    name: props.adSet.name,
  },
});

const onSubmit = handleSubmit(async (values) => {
  if (!meta.value.dirty) {
    isOpen.value = false;
    return;
  }

  const newName = values.name;
  const oldName = props.adSet.name;

  try {
    const { data: adStructure } =
      await AdStructureApi.getAdStructureByChannelGroup(
        brandId,
        campaignId,
        props.channelGroupId,
      );

    const existingAdSets = adStructure.ad_sets;

    if (
      existingAdSets.some((adSet) => adSet.name === newName) &&
      newName !== oldName
    ) {
      generalErrorMessage.value = t(
        "funnel-flow.paid-social.structure.new-structure.errors.duplicated-ad-set-names",
      );
      return;
    }

    const updatedAdSets = existingAdSets.map((adSet) => ({
      id: adSet.id,
      name: adSet.id === props.adSet.id ? newName : adSet.name,
    }));

    await AdStructureApi.updateAdStructure(
      brandId,
      campaignId,
      props.channelGroupId,
      props.adStructureId,
      updatedAdSets,
    );

    emit("saved", { id: props.adSet.id, name: newName });
    isOpen.value = false;
  } catch (error) {
    console.error("Failed to update ad set name:", error);
  } finally {
  }
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
      {{ $t("funnel-flow.paid-social.structure.edit-modal.title") }}
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-10">
      <FieldTextarea
        name="name"
        :label="
          $t('funnel-flow.paid-social.structure.edit-modal.ad-set-name.label')
        "
        :placeholder="
          $t(
            'funnel-flow.paid-social.structure.edit-modal.ad-set-name.placeholder',
          )
        "
      />

      <Alert v-if="generalErrorMessage" type="error" autoScroll>
        {{ generalErrorMessage }}
      </Alert>
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
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
