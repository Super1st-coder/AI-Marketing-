<script setup lang="ts">
import { object, string, number, array, mixed, boolean } from "yup";
import { Country, Income, Location } from "@/services/projects/AudienceApi";
import { toTypedSchema } from "@vee-validate/yup";

const { t } = useI18n();

const formStore = createAudienceStore();
const { createManualForm } = storeToRefs(formStore);

const brandId = useBrandId();
const campaignId = useCampaignId();

const props = defineProps<{
  adsIncomeLevels: {
    label: string;
    value: Income;
  }[];
}>();

const wizard = useFunnelPaidSocialAudienceStore();

const minAgeOptions: { label: string; value: number }[] = [
  { label: "18", value: 18 },
  { label: "25", value: 25 },
  { label: "35", value: 35 },
  { label: "45", value: 45 },
  { label: "55", value: 55 },
];

const maxAgeOptions: { label: string; value: number }[] = [
  { label: "24", value: 24 },
  { label: "34", value: 34 },
  { label: "44", value: 44 },
  { label: "54", value: 54 },
  { label: "64", value: 64 },
  { label: "65+", value: 65 },
];

const genderOptions = computed(() => [
  {
    label: t(
      "funnel-flow.paid-social.audience.create-audience-modal.fields.gender.options.all",
    ),
    value: "All",
  },
  {
    label: t(
      "funnel-flow.paid-social.audience.create-audience-modal.fields.gender.options.male",
    ),
    value: "Male",
  },
  {
    label: t(
      "funnel-flow.paid-social.audience.create-audience-modal.fields.gender.options.female",
    ),
    value: "Female",
  },
]);

const schema = toTypedSchema(
  object({
    name: string()
      .required(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.name.required",
        ),
      )
      .min(
        3,
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.name.min",
          { n: 3 },
        ),
      )
      .max(
        100,
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.name.max",
          { n: 100 },
        ),
      ),
    gender: string()
      .required(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.gender.required",
        ),
      )
      .oneOf(
        ["Male", "Female", "All"],
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.gender.invalid",
        ),
      ),
    age_min: number()
      .transform((_, original) => {
        if (original === "" || original === "-1" || original === -1)
          return undefined;
        const num = Number(original);
        return Number.isFinite(num) ? num : undefined;
      })
      .required(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.age.start-required",
        ),
      )
      .typeError(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.age.select-valid",
        ),
      ),

    age_max: number()
      .transform((_, original) => {
        if (original === "" || original === "-1" || original === -1)
          return undefined;
        const num = Number(original);
        return Number.isFinite(num) ? num : undefined;
      })
      .required(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.age.end-required",
        ),
      )
      .typeError(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.age.select-valid",
        ),
      )
      .when("age_min", (age_min, schema) => {
        return typeof age_min[0] === "number"
          ? schema.min(
              age_min[0],
              t(
                "funnel-flow.paid-social.audience.create-audience-modal.validation.age.end-must-be-gte",
              ),
            )
          : schema;
      }),
    income_level: mixed<Income>()
      .required(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.income.required",
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
          "funnel-flow.paid-social.audience.create-audience-modal.validation.income.required",
        ),
      ),
    interests: array()
      .transform((val) => (Array.isArray(val) ? val : []))
      .compact((v) => typeof v === "string" && v.trim() === "")
      .min(
        1,
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.interests.required",
        ),
      )
      .of(
        string()
          .trim()
          .min(
            2,
            t(
              "funnel-flow.paid-social.audience.create-audience-modal.validation.interests.item-min",
              { n: 2 },
            ),
          )
          .max(
            100,
            t(
              "funnel-flow.paid-social.audience.create-audience-modal.validation.interests.item-max",
              { n: 100 },
            ),
          )
          .required(),
      )
      .max(
        20,
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.interests.max",
          { n: 20 },
        ),
      )
      .required(),
    locations: array()
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
          "funnel-flow.paid-social.audience.create-audience-modal.validation.location.required",
        ),
      )
      .required(
        t(
          "funnel-flow.paid-social.audience.create-audience-modal.validation.location.required",
        ),
      )
      .default([]),
  }),
);

const selectedLocationIndex = ref<number | null>(null);

const { handleSubmit, errors, resetForm } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    name: "",
    gender: "",
    age_min: -1,
    age_max: -1,
    income_level: undefined,
    interests: [],
    locations: [],
  },
});

const { value: nameField } = useField<string>("name", undefined, {
  initialValue: createManualForm.value.name,
});
const { value: genderField } = useField<string>("gender", undefined, {
  initialValue: createManualForm.value.gender,
});
const { value: ageMinField } = useField<number>("age_min", undefined, {
  initialValue: createManualForm.value.age_min ?? -1,
});
const { value: ageMaxField } = useField<number>("age_max", undefined, {
  initialValue: createManualForm.value.age_max ?? -1,
});
const { value: incomeLevelField } = useField<Income | null>(
  "income_level",
  undefined,
  {
    initialValue: createManualForm.value.income_level!,
  },
);
const { value: interestsField } = useField<string[]>("interests", undefined, {
  initialValue: createManualForm.value.interests,
});
const { value: locationField } = useField<Country[]>("locations", undefined, {
  initialValue: createManualForm.value.location,
});

const activeIndex = ref(0);

function activate(i: number) {
  activeIndex.value = i;
}

const onSubmit = handleSubmit(
  async (values) => {
    const payloadLocation: Location[] = values.locations.map((loc) => ({
      label: loc.label!,
      target_location: loc.targetLocation!,
      lat: loc.lat!,
      lng: loc.lng!,
    }));

    wizard.setStep("GENERATE_AUD_LOADER");

    await wizard.generateAudiencesWithManualData({
      campaign_id: campaignId,
      brand_id: brandId,
      ad_set_id: wizard.selectedAdSet.id,
      ...values,
      locations: payloadLocation,
      description: "",
    });

    formStore.resetManualForm();

    resetForm({
      values: {
        name: "",
        gender: "",
        age_min: -1,
        age_max: -1,
        income_level: undefined,
        interests: [],
        locations: [],
      },
      errors: {},
      touched: {},
    });

    wizard.setStep("GENERATED_AUDIENCE");
  },
  (error) => console.log(error),
);

const manualFormReactive = reactive({
  name: nameField,
  gender: genderField,
  age_min: ageMinField,
  age_max: ageMaxField,
  income_level: incomeLevelField,
  interests: interestsField,
  locations: locationField,
});

const locationText = ref("");
const editingLocationIndex = ref<number | null>(null);

function selectLocation(loc: Country) {
  selectedLocationIndex.value = locationField.value.findIndex(
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

watchEffect(() => {
  formStore.saveManualFormProgress(manualFormReactive);
});

function removeCountry(longName: string) {
  const countryIndex = locationField.value.findIndex(
    (item) => item.longName === longName,
  );
  locationField.value.splice(countryIndex, 1);

  if (selectedLocationIndex.value === countryIndex) {
    selectedLocationIndex.value = null;
    editingLocationIndex.value = null;
    locationText.value = "";
  }
}

onMounted(() => {
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
    {{ $t("funnel-flow.paid-social.audience.create-audience-modal.title") }}
  </h2>

  <hr class="tw:my-5" />

  <div
    class="tw:mb-5 tw:grid tw:grid-cols-2 tw:gap-2 tw:rounded-lg tw:bg-secondary/30 tw:p-1"
  >
    <Button
      @click="activate(0)"
      :variant="activeIndex === 0 ? 'solid' : 'text'"
    >
      {{
        $t(
          "funnel-flow.paid-social.audience.create-audience-modal.tabs.describe",
        )
      }}
    </Button>
    <Button
      @click="activate(1)"
      :variant="activeIndex === 1 ? 'solid' : 'text'"
    >
      {{
        $t(
          "funnel-flow.paid-social.audience.create-audience-modal.tabs.manual-entry",
        )
      }}
    </Button>
  </div>

  <div v-show="activeIndex === 0">
    <FunnelPaidSocialFormAudienceCreateAudienceDescribe />
  </div>

  <div v-show="activeIndex === 1">
    <form @submit.prevent="onSubmit" id="aud-form">
      <h3 class="tw:mb-5 tw:font-bold">
        {{
          $t(
            "funnel-flow.paid-social.audience.create-audience-modal.manual.title",
          )
        }}
      </h3>
      <div class="tw:overflow-y">
        <div class="tw:grid tw:grid-cols-2 tw:gap-5">
          <div class="tw:mb-4">
            <FieldText
              name="name"
              :label="
                $t(
                  'funnel-flow.paid-social.audience.create-audience-modal.fields.audience-name.label',
                )
              "
              :placeholder="
                $t(
                  'funnel-flow.paid-social.audience.create-audience-modal.fields.audience-name.placeholder',
                )
              "
              required
            />
          </div>

          <div class="tw:mb-4">
            <FieldSelect
              class="tw:basis-1/3"
              :label="
                $t(
                  'funnel-flow.paid-social.audience.create-audience-modal.fields.gender.label',
                )
              "
              name="gender"
              :placeholder="
                $t(
                  'funnel-flow.paid-social.audience.create-audience-modal.fields.gender.placeholder',
                )
              "
              :options="genderOptions"
            />
          </div>
        </div>

        <div class="tw:grid tw:grid-cols-2 tw:gap-5">
          <div class="tw:mb-4">
            <label
              class="tw:block tw:text-left tw:text-lg tw:font-bold"
              :class="{ 'tw:text-error': !!errors.age_min || !!errors.age_max }"
              for="age_min"
            >
              {{
                $t(
                  "funnel-flow.paid-social.audience.create-audience-modal.fields.age.label",
                )
              }}
            </label>

            <div class="tw:grid tw:grid-cols-2 tw:gap-2">
              <FieldSelect
                class="tw:basis-1/3"
                name="age_min"
                :placeholder="
                  $t(
                    'funnel-flow.paid-social.audience.create-audience-modal.fields.age.placeholder',
                  )
                "
                :options="minAgeOptions"
              />

              <FieldSelect
                class="tw:basis-1/3"
                name="age_max"
                :placeholder="
                  $t(
                    'funnel-flow.paid-social.audience.create-audience-modal.fields.age.placeholder',
                  )
                "
                :options="maxAgeOptions"
              />
            </div>
          </div>

          <div class="tw:mb-4">
            <label
              class="tw:block tw:text-left tw:text-lg tw:font-bold"
              :class="{ 'tw:text-error': !!errors.income_level }"
            >
              {{
                $t(
                  "funnel-flow.paid-social.audience.create-audience-modal.fields.income.label",
                )
              }}
            </label>
            <IncomeSelect
              v-model="incomeLevelField"
              :options="props.adsIncomeLevels"
              :placeholder="
                $t(
                  'funnel-flow.paid-social.audience.create-audience-modal.fields.income.placeholder',
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
        </div>

        <div class="tw:mb-4">
          <label
            class="tw:block tw:text-left tw:text-lg tw:font-bold"
            :class="{ 'tw:text-error': !!errors.interests }"
          >
            {{
              $t(
                "funnel-flow.paid-social.audience.create-audience-modal.fields.interest.label",
              )
            }}
          </label>
          <TagInput
            v-model="interestsField"
            :error="!!errors.interests"
            :placeholder="
              $t(
                'funnel-flow.paid-social.audience.create-audience-modal.fields.interest.placeholder',
              )
            "
            :separators="[',']"
            :max="20"
            :aria-invalid="!!errors.interests"
          />
          <p v-if="errors.interests" class="tw:text-md tw:mt-1 tw:text-error">
            {{ errors.interests }}
          </p>
        </div>

        <div class="tw:tm-1 tw:text-sm">
          <label class="tw:block tw:text-left tw:text-lg tw:font-bold">
            {{
              $t(
                "funnel-flow.paid-social.audience.create-audience-modal.fields.location.proposed-locations",
              )
            }}
          </label>

          <ul
            v-if="locationField.length > 0"
            class="tw:flex tw:cursor-text tw:list-disc tw:flex-wrap tw:items-center tw:gap-x-2.5 tw:gap-y-2 tw:rounded-lg tw:border tw:bg-white tw:px-3 tw:py-2.5 tw:pl-4"
          >
            <li
              v-for="(loc, index) in locationField"
              :key="loc.longName"
              :class="[
                'location-pill tw:inline-flex tw:cursor-pointer tw:items-center tw:rounded-2xl tw:text-sm tw:leading-none tw:whitespace-nowrap',
                index === selectedLocationIndex
                  ? 'tw:bg-secondary tw:text-white'
                  : 'tw:bg-[#fff3ea] tw:text-[#5a4d43]',
              ]"
            >
              <div
                @click.stop="selectLocation(loc)"
                class="tw:py-1.5 tw:pl-2.5"
              >
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
            v-if="locationField.length === 0"
          >
            <span
              class="tw:flex-1 tw:border-0 tw:px-0 tw:py-1.5 tw:text-sm tw:placeholder:text-secondary/70 tw:focus:outline-hidden"
            >
              {{
                $t(
                  "funnel-flow.paid-social.audience.create-audience-modal.fields.location.no-locations-selected",
                )
              }}
            </span>
          </div>
          <div class="tw:mb-3 tw:text-secondary">
            {{
              $t(
                "funnel-flow.paid-social.audience.create-audience-modal.fields.location.selected-locations-help",
              )
            }}
          </div>
        </div>

        <div>
          <SegregationContainer
            v-model:locations="locationField"
            :inputText="locationText"
            :error="!!errors.locations"
            :editingIndex="editingLocationIndex"
          />
          <p class="tw:mb-0 tw:text-sm tw:text-secondary">
            {{
              $t(
                "funnel-flow.paid-social.audience.create-audience-modal.fields.location.search-help",
              )
            }}
          </p>
          <p v-if="errors.locations" class="tw:text-md tw:text-error">
            {{ errors.locations }}
          </p>
        </div>
      </div>
      <div>
        <hr class="tw:-mx-10 tw:my-5 tw:border-secondary/30" />
        <div class="tw:flex tw:justify-end tw:gap-4">
          <Button
            @click="wizard.setStep('START')"
            size="md"
            variant="outlined"
            type="button"
            >{{ $t("global.cancel") }}</Button
          >
          <Button id="aud-form" size="md" type="submit" form="aud-form">
            {{
              $t(
                "funnel-flow.paid-social.audience.create-audience-modal.actions.create-audience",
              )
            }}
          </Button>
        </div>
      </div>
    </form>
  </div>
</template>
