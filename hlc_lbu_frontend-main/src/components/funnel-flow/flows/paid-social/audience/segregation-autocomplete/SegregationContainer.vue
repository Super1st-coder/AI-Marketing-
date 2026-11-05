<script setup lang="ts">
import { Country } from "@/services/projects/AudienceApi";
import { lowerCase } from "lodash";
import { useField } from "vee-validate";

const props = defineProps<{
  error: string | boolean;
  inputText?: string;
  editingIndex?: number | null;
}>();

const locationAutocomplete = ref<any>();
const locations = defineModel<Country[]>("locations", { default: () => [] });

const { validate: validateLocation } = useField<Country[]>("locations");

function extractLocationDetails(addressComponents: any[]) {
  const stateTypes = ["administrative_area_level_1"];
  const cityTypes = [
    "locality",
    "administrative_area_level_2",
    "administrative_area_level_3",
  ];
  const neighborhoodTypes = [
    "neighborhood",
    "sublocality",
    "sublocality_level_1",
    "sublocality_level_2",
  ];

  const state = addressComponents.find((c) =>
    stateTypes.some((t) => c.types.includes(t)),
  );
  const city = addressComponents.find((c) =>
    cityTypes.some((t) => c.types.includes(t)),
  );
  const neighborhood = addressComponents.find((c) =>
    neighborhoodTypes.some((t) => c.types.includes(t)),
  );

  return {
    stateName: state ? state.long_name : "",
    cityName: city ? city.long_name : "",
    neighborhoodName: neighborhood ? neighborhood.long_name : "",
  };
}

function isSameLocation(a: Country, b: Country) {
  return (
    a.longName === b.longName &&
    a.state === b.state &&
    a.name === b.name &&
    a.neighborhood === b.neighborhood
  );
}

watch(locationAutocomplete, (valueChanged: any) => {
  if (!valueChanged) return;

  const countryShortNameIndex = valueChanged.addressComponents.findIndex(
    (item) => item.types.includes("country"),
  );

  const countryName =
    countryShortNameIndex !== -1
      ? valueChanged.addressComponents[countryShortNameIndex].long_name
      : "";

  const countryShortName =
    countryShortNameIndex !== -1
      ? lowerCase(
          valueChanged.addressComponents[countryShortNameIndex].short_name,
        )
      : "";

  const { cityName, neighborhoodName, stateName } = extractLocationDetails(
    valueChanged.addressComponents,
  );

  const newLocation = {
    longName: countryName,
    shortName: countryShortName,
    name: cityName,
    state: stateName || "",
    neighborhood: neighborhoodName || "",
    label: valueChanged.label,
    targetLocation: true,
    lat: valueChanged.lat,
    lng: valueChanged.lng,
  };

  const exists = locations.value.some((loc, index) => {
    if (
      props.editingIndex !== null &&
      props.editingIndex !== undefined &&
      index === props.editingIndex
    ) {
      return false;
    }

    return isSameLocation(loc, newLocation);
  });

  if (exists) {
    locationAutocomplete.value = null;
    return;
  }

  if (props.editingIndex !== null && props.editingIndex !== undefined) {
    locations.value.splice(props.editingIndex, 1, newLocation);
    validateLocation();
    locationAutocomplete.value = null;
    return;
  }

  locations.value.push(newLocation);
  validateLocation();
  locationAutocomplete.value = null;
});
</script>

<template>
  <Autocomplete
    v-model="locationAutocomplete"
    :inputText="inputText"
    :label="$t('audience.ai-research.create-audience.location-label')"
    :placeholder="
      $t('audience.ai-research.create-audience.location-placeholder')
    "
    :error="!!props.error"
    dropDirection="down"
  />
</template>
