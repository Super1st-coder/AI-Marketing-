<script setup lang="ts">
import { object, string, number, array, mixed, boolean } from "yup";
import {
  AudienceItem,
  Country,
  Income,
  UpdatePreferredAudienceBody,
} from "@/services/projects/AudienceApi";
import { toTypedSchema } from "@vee-validate/yup";

const props = defineProps<{
  formData: AudienceItem;
  channelId: number;
  adsIncomeLevels: {
    label: string;
    value: Income;
  }[];
}>();

const { t } = useI18n();

const brandId = useBrandId();
const campaignId = useCampaignId();

const wizard = useFunnelPaidSocialAudienceStore();

// Modal state for audience change confirmation
const showAudienceChangeModal = ref(false);
const pendingUpdateBody = ref<UpdatePreferredAudienceBody | null>(null);

const ageOptions = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"].map(
  (a) => ({ label: a, value: a }),
);

const genderOptions = computed(() => [
  {
    label: t(
      "funnel-flow.paid-social.audience.edit-audience-modal.fields.gender.options.all",
    ),
    value: "All",
  },
  {
    label: t(
      "funnel-flow.paid-social.audience.edit-audience-modal.fields.gender.options.male",
    ),
    value: "Male",
  },
  {
    label: t(
      "funnel-flow.paid-social.audience.edit-audience-modal.fields.gender.options.female",
    ),
    value: "Female",
  },
]);

const schema = toTypedSchema(
  object({
    name: string()
      .required(
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.name.required",
        ),
      )
      .min(
        3,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.name.min",
          { n: 3 },
        ),
      )
      .max(
        100,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.name.max",
          { n: 100 },
        ),
      ),
    description: string()
      .required(
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.description.required",
        ),
      )
      .min(
        3,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.description.min",
          { n: 3 },
        ),
      )
      .max(
        300,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.description.max",
          { n: 300 },
        ),
      ),
    gender: string()
      .required(
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.gender.required",
        ),
      )
      .oneOf(
        ["All", "Male", "Female"],
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.gender.invalid",
        ),
      ),
    age: array()
      .of(string())
      .min(
        1,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.age.required",
        ),
      )
      .typeError(
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.age.select-valid",
        ),
      ),
    income_level: mixed<Income>()
      .required(
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.income.required",
        ),
      )
      .oneOf(
        [
          "Struggling to cover basic needs.",
          "Budget-conscious, limited discretionary income.",
          "Balanced finances, occasional treats.",
          "Comfortable, prioritizes experiences and quality.",
          "High-income, enjoying premium lifestyles.",
          "Extremely wealthy with luxury preferences.",
        ],
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.income.required",
        ),
      ),
    interests: array()
      .transform((val) => (Array.isArray(val) ? val : []))
      .compact((v) => typeof v === "string" && v.trim() === "")
      .min(
        1,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.interests.required",
        ),
      )
      .of(
        string()
          .trim()
          .min(
            2,
            t(
              "funnel-flow.paid-social.audience.edit-audience-modal.validation.interests.item-min",
              { n: 2 },
            ),
          )
          .max(
            100,
            t(
              "funnel-flow.paid-social.audience.edit-audience-modal.validation.interests.item-max",
              { n: 100 },
            ),
          )
          .required(),
      )
      .max(
        20,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.interests.max",
          { n: 20 },
        ),
      )
      .required(),
    location: array()
      .of(
        object({
          longName: string(),
          shortName: string(),
          cities: array(),
          label: string(),
          name: string(),
          targetLocation: boolean(),
          state: string(),
          neighborhood: string(),
          lat: number(),
          lng: number(),
        }),
      )
      .min(
        1,
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.location.required",
        ),
      )
      .required(
        t(
          "funnel-flow.paid-social.audience.edit-audience-modal.validation.location.required",
        ),
      )
      .default([]),
  }),
);

const { handleSubmit, errors, setValues, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    name: props.formData.name,
    description: props.formData.description,
    gender: props.formData.gender,
    age: props.formData.age,
    income_level: props.formData?.income,
    interests: props.formData?.interests,
    location: mapLocations(props.formData?.location),
  },
});

const selectedLocationIndex = ref<number | null>(null);

watch(
  () => props.formData,
  (newForm) => {
    if (!newForm) return;
    setValues({
      name: newForm.name,
      description: newForm.description,
      gender: newForm.gender,
      age: newForm.age,
      income_level: newForm?.income,
      interests: newForm?.interests,
      location: normalizeTags(newForm?.location),
    });

    setTimeout(() => {
      location.value = normalizeTags(newForm.location);
    }, 0);
  },
  { immediate: true },
);

function mapLocations(location: Country[] | string[]): Country[] {
  const newLocationVal = JSON.parse(JSON.stringify(location));
  if (
    Array.isArray(newLocationVal) &&
    newLocationVal.every((el) => typeof el === "string")
  ) {
    return [];
  }
  return newLocationVal;
}

const { value: name } = useField<string>("name");
const { value: description } = useField<string>("description");
const { value: gender } = useField<string>("gender");
const { value: age } = useField<string[] | null>("age");
const { value: income_level } = useField<Income>("income_level");
const { value: interests } = useField<string[]>("interests");
const { value: location } = useField<Country[]>("location");

const onSubmit = handleSubmit(async () => {
  const body: UpdatePreferredAudienceBody = {
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: wizard.selectedAdSet.id,
    channel_id: props.channelId,
    preferred_audience: {
      name: name.value,
      description: description.value,
      gender: gender.value,
      age: age.value!,
      income: income_level.value,
      interests: interests.value,
      location: location.value,
      saved: props.formData.saved,
      id: props.formData.id,
      preferred: props.formData.preferred,
      comments: props.formData.comments,
    },
  };

  // Only show confirmation modal if form is dirty and ad set has filled ads
  if (meta.value.dirty && wizard.selectedAdSetHasFilledAds) {
    pendingUpdateBody.value = body;
    showAudienceChangeModal.value = true;
  } else {
    await wizard.updatePreferredAudience(body);
    wizard.closeAllModals();
  }
});

async function submitPendingUpdate() {
  if (!pendingUpdateBody.value) return;

  await wizard.updatePreferredAudience(pendingUpdateBody.value);
  pendingUpdateBody.value = null;
  wizard.closeAllModals();
}

const locationText = ref("");
const editingLocationIndex = ref<number | null>(null);

function selectLocation(loc: Country) {
  selectedLocationIndex.value = location.value.findIndex(
    (item) =>
      item.longName === loc.longName &&
      item.state === loc.state &&
      item.name === loc.name,
  );

  editingLocationIndex.value = selectedLocationIndex.value;

  const parts = [loc.longName, loc.state, loc.name, loc.neighborhood].filter(
    (v) => v && v.trim(),
  );

  locationText.value = "";
  nextTick(() => {
    locationText.value = parts.join(", ");
  });
}

function removeCountry(longName: string) {
  const countryIndex = location.value.findIndex(
    (item) => item.longName === longName,
  );
  location.value.splice(countryIndex, 1);

  if (selectedLocationIndex.value === countryIndex) {
    selectedLocationIndex.value = null;
    editingLocationIndex.value = null;
    locationText.value = "";
  }
}

function normalizeTags(location): Country[] {
  let result: Country[] = [];
  result = location.map((item) => {
    if (typeof item === "string") {
      return {
        longName: item.trim(),
      };
    }
    return item;
  });

  return result;
}

onMounted(() => {
  location.value = normalizeTags(props.formData.location);
  document.addEventListener("mousedown", onOutsideClick);
});

function onOutsideClick(e: MouseEvent) {
  const target = e.target as HTMLElement;

  const isPill = !!target.closest(".location-pill");
  const isAutocompleteOption =
    !!target.closest(".options-container") ||
    target.getAttribute("role") === "option";

  if (!isPill && !isAutocompleteOption) {
    selectedLocationIndex.value = null;
    editingLocationIndex.value = null;
    locationText.value = "";
  }
}
</script>

<template>
  <h2 class="tw:mb-4 tw:text-2xl tw:font-extrabold">
    {{ $t("funnel-flow.paid-social.audience.edit-audience-modal.title") }}
  </h2>

  <hr class="tw:my-5 tw:border-secondary/30" />

  <form @submit.prevent="onSubmit" @keydown.enter.prevent id="edit-aud-form">
    <h3 class="tw:mb-5 tw:font-bold">
      {{
        $t("funnel-flow.paid-social.audience.edit-audience-modal.form.title")
      }}
    </h3>
    <div class="tw:overflow-y">
      <div class="tw:mb-4">
        <FieldText
          name="name"
          :label="
            $t(
              'funnel-flow.paid-social.audience.edit-audience-modal.fields.audience-name.label',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.audience.edit-audience-modal.fields.audience-name.placeholder',
            )
          "
          required
        />
      </div>

      <div class="tw:mb-4">
        <FieldTextarea
          name="description"
          :label="
            $t(
              'funnel-flow.paid-social.audience.edit-audience-modal.fields.description.label',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.audience.edit-audience-modal.fields.description.placeholder',
            )
          "
          required
        />
      </div>

      <div class="tw:grid tw:grid-cols-2 tw:gap-5">
        <div class="tw:mb-4">
          <FieldSelect
            class="tw:basis-1/3"
            :label="
              $t(
                'funnel-flow.paid-social.audience.edit-audience-modal.fields.gender.label',
              )
            "
            name="gender"
            :placeholder="
              $t(
                'funnel-flow.paid-social.audience.edit-audience-modal.fields.gender.placeholder',
              )
            "
            :options="genderOptions"
          />
        </div>

        <div class="tw:mb-4">
          <label
            class="tw:-mt-1 tw:block tw:text-left tw:text-lg tw:font-bold"
            for="age_min"
            :class="{ 'tw:text-error': !!errors.age }"
          >
            {{
              $t(
                "funnel-flow.paid-social.audience.edit-audience-modal.fields.age.label",
              )
            }}
          </label>

          <IncomeSelect
            v-model="age"
            :options="ageOptions"
            :multiple="true"
            :placeholder="
              $t(
                'funnel-flow.paid-social.audience.edit-audience-modal.fields.age.placeholder',
              )
            "
            :aria-invalid="!!errors.age"
            :aria-describedby="errors.age ? 'err-income' : undefined"
            :error="errors.age"
          />
          <div class="tw:mt-1 tw:grid tw:grid-cols-2 tw:gap-2">
            <p v-if="errors.age" class="tw:text-md tw:text-error">
              {{ errors.age }}
            </p>
          </div>
        </div>
      </div>

      <div class="tw:mb-4">
        <label
          class="tw:block tw:text-left tw:text-lg tw:font-bold"
          :class="{ 'tw:text-error': !!errors.income_level }"
        >
          {{
            $t(
              "funnel-flow.paid-social.audience.edit-audience-modal.fields.income.label",
            )
          }}
        </label>

        <IncomeSelect
          v-model="income_level"
          :options="props.adsIncomeLevels"
          :placeholder="
            $t(
              'funnel-flow.paid-social.audience.edit-audience-modal.fields.income.placeholder',
            )
          "
          :aria-invalid="!!errors.income_level"
          :aria-describedby="errors.income_level ? 'err-income' : undefined"
          :class="{ 'tw:border-red-500': !!errors.income_level }"
          :error="errors.income_level"
        />
        <p
          v-if="errors.income_level"
          id="err-income"
          class="tw:text-md tw:mt-1 tw:text-error"
        >
          {{ errors.income_level }}
        </p>
      </div>

      <div class="tw:mb-4">
        <label
          class="tw:block tw:text-left tw:text-lg tw:font-bold"
          :class="{ 'tw:text-error': !!errors.interests }"
        >
          {{
            $t(
              "funnel-flow.paid-social.audience.edit-audience-modal.fields.interest.label",
            )
          }}
        </label>
        <TagInput
          v-model="interests"
          :placeholder="
            $t(
              'funnel-flow.paid-social.audience.edit-audience-modal.fields.interest.placeholder',
            )
          "
          :separators="[',']"
          :max="20"
          :aria-invalid="!!errors.interests"
          :error="!!errors.interests"
        />
        <p v-if="errors.interests" class="tw:text-md tw:mt-1 tw:text-error">
          {{ errors.interests }}
        </p>
      </div>

      <div class="tw:tm-1 tw:text-sm">
        <label class="tw:block tw:text-left tw:text-lg tw:font-bold">
          {{
            $t(
              "funnel-flow.paid-social.audience.edit-audience-modal.fields.location.proposed-locations",
            )
          }}
        </label>

        <ul
          v-if="location.length > 0"
          class="tw:flex tw:cursor-text tw:list-disc tw:flex-wrap tw:items-center tw:gap-x-2.5 tw:gap-y-2 tw:rounded-lg tw:border tw:bg-white tw:px-3 tw:py-2.5 tw:pl-4"
        >
          <li
            v-for="(loc, index) in location"
            :key="loc.longName"
            :class="[
              'location-pill tw:inline-flex tw:cursor-pointer tw:items-center tw:rounded-2xl tw:text-sm tw:leading-none tw:whitespace-nowrap',
              index === selectedLocationIndex
                ? 'tw:bg-secondary tw:text-white'
                : 'tw:bg-[#fff3ea] tw:text-[#5a4d43]',
            ]"
          >
            <div @click.stop="selectLocation(loc)" class="tw:py-1.5 tw:pl-2.5">
              {{
                [loc.longName, loc.state, loc.name, loc.neighborhood]
                  .filter((v) => v && v.trim())
                  .join(", ")
              }}
            </div>

            <button
              type="button"
              @click.stop="removeCountry(loc.longName)"
              class="tw:px-2.5 tw:py-1.5 tw:text-base tw:leading-none tw:hover:opacity-80"
            >
              ×
            </button>
          </li>
        </ul>

        <div
          class="tw:flex tw:cursor-text tw:list-disc tw:flex-wrap tw:items-center tw:gap-x-2.5 tw:gap-y-2 tw:rounded-lg tw:border tw:bg-white tw:px-3 tw:py-2.5 tw:pl-4 tw:text-secondary"
          v-if="location.length === 0"
        >
          <span
            class="tw:flex-1 tw:border-0 tw:px-0 tw:py-1.5 tw:text-sm tw:placeholder:text-secondary/70 tw:focus:outline-hidden"
          >
            {{
              $t(
                "funnel-flow.paid-social.audience.edit-audience-modal.fields.location.no-locations-selected",
              )
            }}
          </span>
        </div>
        <p class="tw:mb-3 tw:text-secondary">
          {{
            $t(
              "funnel-flow.paid-social.audience.edit-audience-modal.fields.location.selected-locations-help",
            )
          }}
        </p>
      </div>

      <div>
        <SegregationContainer
          v-model:locations="location"
          :inputText="locationText"
          :error="!!errors.location"
          :editingIndex="editingLocationIndex"
        />
        <p class="tw:mb-0 tw:text-sm tw:text-secondary">
          {{
            $t(
              "funnel-flow.paid-social.audience.edit-audience-modal.fields.location.search-help",
            )
          }}
        </p>
        <p v-if="errors.location" class="tw:text-md tw:text-error">
          {{ errors.location }}
        </p>
      </div>
    </div>
    <div>
      <hr class="tw:-mx-10 tw:my-5 tw:border-secondary/30" />
      <div class="tw:flex tw:justify-end tw:gap-4">
        <Button
          @click="wizard.closeAllModals"
          size="md"
          variant="outlined"
          type="button"
          >{{ $t("global.cancel") }}</Button
        >
        <Button size="md" type="submit" form="edit-aud-form">
          {{
            $t(
              "funnel-flow.paid-social.audience.edit-audience-modal.actions.save-changes",
            )
          }}
        </Button>
      </div>
    </div>
  </form>

  <!-- Target Audience Changed Modal -->
  <FunnelPaidSocialFormAudienceChangeModal
    v-model="showAudienceChangeModal"
    :adSetId="wizard.selectedAdSet.id"
    :channelId="props.channelId"
    @confirm="submitPendingUpdate"
  />
</template>
