<template>
  <div ref="root" class="tw:relative" :class="wrapperClass">
    <label
      v-if="label"
      class="tw:block tw:text-left tw:text-lg tw:font-bold"
      :class="{
        'tw:text-error': error,
      }"
    >
      {{ label }}
    </label>

    <div class="tw:relative">
      <input
        ref="inputRef"
        :value="query"
        @input="onInput"
        @focus="openList()"
        @keydown="onKeyDown"
        :placeholder="placeholder"
        :disabled="disabled"
        role="combobox"
        :aria-expanded="open"
        aria-autocomplete="list"
        :aria-controls="listId"
        :aria-activedescendant="
          activeIndex >= 0 ? `${listId}-opt-${activeIndex}` : undefined
        "
        :aria-label="
          inputAriaLabel ||
          label ||
          t(
            'funnel-flow.paid-social.audience.segregation-autocomplete.aria.input',
          )
        "
        class="tw:block tw:w-full tw:rounded-lg tw:border tw:bg-white tw:px-4 tw:py-2 tw:focus:ring-2"
        :class="{
          'tw:border-error tw:focus:border-error': error,
          'tw:border-secondary/30': !error,
        }"
      />

      <button
        v-if="query"
        type="button"
        @click="clearSelection"
        class="tw:hover:bg-neutral-100 tw:absolute tw:top-1/2 tw:right-9 tw:-translate-y-1/2 tw:rounded-full tw:p-1"
        :aria-label="
          t(
            'funnel-flow.paid-social.audience.segregation-autocomplete.aria.clear',
          )
        "
      >
        <svg aria-hidden viewBox="0 0 24 24" class="tw:h-4 tw:w-4">
          <path
            d="M6 6l12 12M18 6L6 18"
            stroke="currentColor"
            stroke-width="2"
            fill="none"
          />
        </svg>
      </button>

      <button
        type="button"
        class="tw:hover:bg-neutral-100 tw:absolute tw:top-1/2 tw:right-2 tw:-translate-y-1/2 tw:rounded-full tw:p-1"
        :aria-label="
          open
            ? t(
                'funnel-flow.paid-social.audience.segregation-autocomplete.aria.close-list',
              )
            : t(
                'funnel-flow.paid-social.audience.segregation-autocomplete.aria.open-list',
              )
        "
        @click="toggle"
      >
        <svg
          aria-hidden
          viewBox="0 0 24 24"
          class="tw:h-5 tw:w-5 tw:transition"
          :class="open ? 'tw:rotate-180' : ''"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      <ul
        v-show="open"
        ref="listRef"
        :id="listId"
        role="listbox"
        class="options-container tw:absolute tw:z-50 tw:max-h-64 tw:w-full tw:overflow-auto tw:rounded-xl tw:border tw:bg-white tw:shadow-xl"
        :class="dropUp ? 'tw:bottom-full tw:mb-2' : 'tw:top-full tw:mt-2'"
      >
        <li
          v-if="loading"
          class="tw:text-neutral-500 tw:px-4 tw:py-3 tw:text-sm"
        >
          {{
            t(
              "funnel-flow.paid-social.audience.segregation-autocomplete.searching",
            )
          }}
        </li>

        <li
          v-else-if="
            !loading && query.trim() && options.length === 0 && hasSearched
          "
          class="tw:text-neutral-500 tw:px-4 tw:py-3 tw:text-sm"
        >
          {{ emptyText }}
        </li>

        <li
          v-for="(opt, i) in options"
          :key="opt.value"
          :id="`${listId}-opt-${i}`"
          role="option"
          :aria-selected="isSelected(opt)"
          class="tw:hover:bg-neutral-50 tw:flex tw:cursor-pointer tw:items-center tw:justify-between tw:px-4 tw:py-3 tw:text-sm tw:transition"
          :class="
            i === activeIndex
              ? 'tw:text-neutral-900 tw:bg-secondary/20 tw:font-medium'
              : ''
          "
          @mousemove="activeIndex = i"
          @mousedown.prevent
          @click="commit(opt)"
        >
          <span class="tw:truncate">{{ opt.label }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import useGoogleMaps from "@/composables/useGoogleMaps";
const { t } = useI18n();

type Option = {
  label: string;
  value: string;
  addressComponents: any[] | undefined;
  lat: number;
  lng: number;
};

type DropDirection = "auto" | "down" | "up";

const props = defineProps<{
  modelValue?: Option | null;
  inputText?: string;
  placeholder?: string;
  disabled?: boolean;
  emptyText?: string;
  label?: string;
  wrapperClass?: string;
  inputAriaLabel?: string;
  country?: string;
  error?: string | boolean;
  dropDirection?: DropDirection;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: Option | null): void;
}>();

const placeholder = computed(() => props.placeholder ?? "");
const disabled = computed(() => props.disabled ?? false);
const emptyText = computed(
  () =>
    props.emptyText ??
    t(
      "funnel-flow.paid-social.audience.segregation-autocomplete.location-not-found",
    ),
);
const label = computed(() => props.label);
const wrapperClass = computed(() => props.wrapperClass ?? "");
const inputAriaLabel = computed(() => props.inputAriaLabel);
const loading = ref(false);
const hasSearched = ref(false);

const open = ref(false);
const query = ref<string>(props.modelValue?.label ?? "");
const activeIndex = ref(-1);
const dropUp = ref(false);

const root = ref<HTMLDivElement | null>(null);
const inputRef = ref<HTMLInputElement | null>(null);
const listRef = ref<HTMLUListElement | null>(null);
const listId = `ac-${Math.random().toString(36).slice(2)}`;

const options = ref<Option[]>([]);
let googleRef: typeof google | null = null;
let autocompleteService: google.maps.places.AutocompleteService | null = null;
let placesService: google.maps.places.PlacesService | null = null;

const suppressWatch = ref(false);

const error = computed(() => props.error);

const dropDirection = computed<DropDirection>(
  () => props.dropDirection ?? "auto",
);

watch(
  () => props.modelValue,
  (v) => {
    if (suppressWatch.value) return;
    query.value = v?.label ?? "";
  },
);

watch(
  () => props.inputText,
  (val) => {
    if (!val) {
      query.value = "";
      options.value = [];
      return;
    }

    query.value = val;
    open.value = true;
    hasSearched.value = false;
    fetchGooglePlaces(val);
  },
  { immediate: false },
);

function debounce<T extends (...args: any[]) => void>(fn: T, ms: number) {
  let t: number | undefined;
  return (...args: Parameters<T>) => {
    window.clearTimeout(t);
    t = window.setTimeout(() => fn(...args), ms);
  };
}

const fetchGooglePlaces = debounce((search: string) => {
  if (!googleRef) return;
  if (!autocompleteService) {
    autocompleteService = new googleRef.maps.places.AutocompleteService();
  }
  loading.value = true;
  hasSearched.value = true;
  autocompleteService.getPlacePredictions(
    {
      input: search,
      componentRestrictions: props.country
        ? { country: props.country }
        : undefined,
    },
    (predictions) => {
      loading.value = false;

      if (!predictions) {
        options.value = [];
        return;
      }
      options.value = predictions.map((p) => ({
        label: p.description,
        value: p.place_id,
        addressComponents: [],
        lat: 0,
        lng: 0,
      }));
    },
  );
}, 200);

function onInput(e: Event) {
  const val = (e.target as HTMLInputElement).value;
  query.value = val;

  if (val.trim()) {
    open.value = true;
    fetchGooglePlaces(val.trim());
  } else {
    open.value = false;
    options.value = [];
  }

  activeIndex.value = -1;
  nextTick(() => adjustDropdownPosition());
}

function commit(option: Option | null) {
  suppressWatch.value = true;

  if (option && googleRef && !placesService && inputRef.value) {
    placesService = new googleRef.maps.places.PlacesService(inputRef.value);
  }

  if (option && placesService) {
    placesService.getDetails(
      {
        placeId: option.value,
        fields: ["geometry", "name", "address_components"],
      },
      (place, status) => {
        if (
          status === googleRef!.maps.places.PlacesServiceStatus.OK &&
          place?.geometry?.location
        ) {
          const country = place.address_components?.find((c) =>
            c.types.includes("country"),
          );

          option.addressComponents = place?.address_components;

          const isAllowed =
            !props.country ||
            country?.short_name?.toLowerCase() === props.country.toLowerCase();

          if (isAllowed) {
            option.lat = place.geometry.location.lat();
            option.lng = place.geometry.location.lng();
            emit("update:modelValue", option);
            query.value = option.label;
          } else {
            emit("update:modelValue", null);
            query.value = "";
          }

          query.value = "";
          nextTick(() => (suppressWatch.value = false));
        }
      },
    );
  } else {
    emit("update:modelValue", option);
  }

  query.value = "";
  open.value = false;
  activeIndex.value = -1;
  nextTick(() => inputRef.value?.focus());
}

function clearSelection() {
  emit("update:modelValue", null);
  query.value = "";
  options.value = [];
  activeIndex.value = -1;
}

function isSelected(opt: Option) {
  return props.modelValue?.value === opt.value;
}

function onKeyDown(e: KeyboardEvent) {
  if (!open.value && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
    open.value = true;
    activeIndex.value = 0;
    return;
  }
  switch (e.key) {
    case "ArrowDown":
      e.preventDefault();
      activeIndex.value = Math.min(
        activeIndex.value + 1,
        options.value.length - 1,
      );
      break;
    case "ArrowUp":
      e.preventDefault();
      activeIndex.value = Math.max(activeIndex.value - 1, 0);
      break;
    case "Enter":
      if (open.value && activeIndex.value >= 0) {
        e.preventDefault();
        commit(options.value[activeIndex.value]);
      }
      break;
    case "Escape":
      e.preventDefault();
      open.value = false;
      activeIndex.value = -1;
      break;
  }
}

function adjustDropdownPosition() {
  if (dropDirection.value === "down") {
    dropUp.value = false;
    return;
  }

  if (dropDirection.value === "up") {
    dropUp.value = true;
    return;
  }

  if (!inputRef.value || !listRef.value) return;

  const inputRect = inputRef.value.getBoundingClientRect();
  const viewportHeight = window.innerHeight;
  const listHeight = Math.min(listRef.value.scrollHeight, 256);
  const spaceBelow = viewportHeight - inputRect.bottom;
  const spaceAbove = inputRect.top;

  dropUp.value = spaceBelow < listHeight && spaceAbove > spaceBelow;
}

function openList() {
  if (disabled.value) return;
  if (!query.value.trim()) return;
  open.value = true;
  nextTick(() => adjustDropdownPosition());
}

function toggle() {
  if (disabled.value) return;
  if (!query.value.trim()) {
    open.value = false;
    return;
  }
  open.value = !open.value;
}

function onDocClick(ev: MouseEvent) {
  if (!root.value) return;
  if (!root.value.contains(ev.target as Node)) {
    open.value = false;
    activeIndex.value = -1;
  }
}

onMounted(async () => {
  // Carga Google Maps (una sola vez en toda la app)
  try {
    googleRef = await useGoogleMaps(["places"]);
  } catch (err) {
    console.error("Error cargando Google Maps:", err);
  }

  document.addEventListener("mousedown", onDocClick);
  window.addEventListener("resize", adjustDropdownPosition);
  window.addEventListener("scroll", adjustDropdownPosition, true);
});

onUnmounted(() => {
  document.removeEventListener("mousedown", onDocClick);
  window.removeEventListener("resize", adjustDropdownPosition);
  window.removeEventListener("scroll", adjustDropdownPosition, true);
});

defineExpose({ clear: clearSelection });
</script>

<style scoped>
.autocomplete-input,
.options-container {
  border: 1px solid #e7e3df;
}
</style>
