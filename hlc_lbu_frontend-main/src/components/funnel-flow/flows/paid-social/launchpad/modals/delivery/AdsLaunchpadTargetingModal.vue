<script setup lang="ts">
import { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import { toTypedSchema } from "@vee-validate/yup";
import { array, object } from "yup";
import ChannelConnections, {
  LaunchPreCheckLocation,
} from "@/services/funnel-flow/ChannelConnections";
import { useDebounce } from "@vueuse/core";
import { upperFirst } from "lodash";

const props = defineProps<{
  creativeId: number;
  // The summary shows the checks without allowing changes
  readonly?: boolean;
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

// Error message from API
const generalErrorMessage = ref<string | undefined>(undefined);

const searchOptions = ref<AutocompleteOption[]>([]);
const loading = ref<boolean>(false);
const search = ref<string | undefined>(undefined);
const debouncedSearch = useDebounce(search, 500);

const getType = (location: LaunchPreCheckLocation) => {
  return upperFirst(location.type);
};

const formatLocationName = (location: LaunchPreCheckLocation): string => {
  return location.region
    ? `${location.name} - ${location.region} (${getType(location)})`
    : `${location.name}  (${getType(location)})`;
};

// Fetch search options when search (debounced) changes
watch(debouncedSearch, async (search) => {
  if (!search) {
    searchOptions.value = [];
    return;
  }

  loading.value = true;
  try {
    const locations = await ChannelConnections.searchMetaLocations(search);
    searchOptions.value = locations.map((location) => ({
      value: location,
      label: formatLocationName(location),
    }));
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
});

// Clear search options when search is cleared
watch(search, async (search) => {
  if (!search) {
    searchOptions.value = [];
  }
});

const schema = computed(() =>
  toTypedSchema(
    object({
      location: array()
        .required(t("forms.required-field"))
        .min(
          1,
          t(
            "funnel-flow.paid-social.launchpad.targeting-modal.validation.at-least-one-location",
          ),
        ),
    }),
  ),
);

const { handleSubmit, meta, values, isSubmitting, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      location: preCheckStore.getLocations(props.creativeId) ?? [],
    },
  });

// Clear API error when user changes the form value
watch(
  () => values.location,
  () => {
    if (generalErrorMessage.value) {
      generalErrorMessage.value = undefined;
    }
  },
);

const onSubmit = handleSubmit(async (values) => {
  if (props.readonly) {
    return;
  }

  try {
    await preCheckStore.setLocations(props.creativeId, values.location);

    isOpen.value = false;
  } catch (error: any) {
    const errorCode = error?.message?.code;

    if (errorCode) {
      generalErrorMessage.value =
        error?.message?.message ||
        t("funnel-flow.paid-social.launchpad.targeting-modal.errors.generic");
    } else {
      throw error;
    }
  }
});

const handleCancel = () => {
  isOpen.value = false;
};

// Proposal locations from precheck (display-only chips)
const proposalLocations = computed(() => {
  const creative = preCheckStore.getInitialCreative(props.creativeId);
  const locations = creative?.proposal_locations ?? [];

  return locations.map(
    (location) => location.longName ?? location.label ?? location,
  );
});

// Remove a location from selected locations
const removeLocation = (locationToRemove: LaunchPreCheckLocation) => {
  const currentLocations = values.location ?? [];

  setFieldValue(
    "location",
    currentLocations.filter(
      (loc: LaunchPreCheckLocation) => loc.key !== locationToRemove.key,
    ),
  );
};

const searchFieldWrapperRef = ref<HTMLElement | null>(null);

const applyProposalToSearch = async (locationLabel: string) => {
  const input = searchFieldWrapperRef.value?.querySelector("input");
  input?.focus();
  await nextTick();
  search.value = locationLabel;
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    useCustomClose
    @customClose="handleCancel"
    alignment="top"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.launchpad.targeting-modal.title") }}

      <template #description>
        {{
          $t("funnel-flow.paid-social.launchpad.targeting-modal.description")
        }}
      </template>

      <template #after>
        <Alert v-if="generalErrorMessage" type="error" class="tw:mt-6">
          <strong>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.targeting-modal.error-prefix",
              )
            }}
          </strong>
          {{ generalErrorMessage }}
        </Alert>
        <Alert
          v-else
          :type="meta.valid ? 'success' : 'warning'"
          class="tw:mt-6"
        >
          <template v-if="meta.valid">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.targeting-modal.validation.passed",
              )
            }}
          </template>
          <template v-else>
            <strong>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.targeting-modal.validation.action-required-prefix",
                )
              }}
            </strong>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.targeting-modal.validation.action-required-message",
              )
            }}
          </template>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <!-- Strategic proposal -->
      <div v-if="proposalLocations.length > 0" class="tw:mb-5">
        <FieldLabel class="tw:mb-2">
          {{
            $t(
              "funnel-flow.paid-social.launchpad.targeting-modal.strategic-proposal",
            )
          }}
        </FieldLabel>
        <div class="tw:flex tw:flex-wrap tw:gap-2">
          <Chip
            v-for="location in proposalLocations"
            :key="location"
            variant="label"
            color="primary"
            size="md"
            :class="{ 'tw:cursor-pointer': !readonly }"
            @click="!readonly && applyProposalToSearch(location)"
          >
            {{ location }}
          </Chip>
        </div>
      </div>

      <!-- Search locations -->
      <div ref="searchFieldWrapperRef">
        <FieldAutocomplete
          name="location"
          :disabled="readonly"
          :label="
            $t(
              'funnel-flow.paid-social.launchpad.targeting-modal.search-locations',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.launchpad.targeting-modal.location-placeholder',
            )
          "
          :options="searchOptions"
          multiple
          chips
          closableChips
          hideDetails
          hideNoData
          hideSelections
          v-model:search="search"
          :loading="loading"
          disableClientFilter
          class="tw:mb-5"
        />
      </div>

      <!-- Selected locations -->
      <div class="tw:mb-5">
        <FieldLabel class="tw:mb-2">
          {{
            $t(
              "funnel-flow.paid-social.launchpad.targeting-modal.selected-locations",
            )
          }}
        </FieldLabel>

        <div
          v-if="values.location && values.location.length > 0"
          class="tw:flex tw:flex-wrap tw:gap-2"
        >
          <Chip
            v-for="location in values.location"
            :key="location.key"
            variant="label"
            color="primary"
            size="md"
            class="tw:group"
          >
            {{ formatLocationName(location) }}

            <button
              v-if="!readonly"
              type="button"
              class="tw:ml-1 tw:flex tw:items-center tw:justify-center tw:rounded"
              :aria-label="
                $t('funnel-flow.paid-social.launchpad.targeting-modal.remove')
              "
              @click="removeLocation(location)"
            >
              <Icon icon="tabler-x" class="tw:text-base" />
            </button>
          </Chip>
        </div>
        <div v-else>
          <FieldHint>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.targeting-modal.no-locations-selected",
              )
            }}
          </FieldHint>
        </div>
      </div>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        @click="handleCancel"
      >
        {{ $t("global.close") }}
      </Button>

      <Button
        v-if="!readonly"
        type="submit"
        :disabled="!meta.valid"
        :isLoading="isSubmitting"
      >
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
