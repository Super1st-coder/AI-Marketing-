<script setup lang="ts">
import {
  brandFormColorCategories,
  BrandFormColorCategory,
  type BrandColor,
} from "@/services/NewBrandsApi";
import { BrandFormColor } from "./BrandFormTabColors.vue";
import { useTabsContext } from "@/components/tabs/useTabsContext";
import BrandFormTabOverviewColor from "./overview/BrandFormTabOverviewColor.vue";
import BrandFormTabOverviewLogo from "./overview/BrandFormTabOverviewLogo.vue";
import BrandFormTabOverviewTypography from "./overview/BrandFormTabOverviewTypography.vue";
import BrandFormTabOverviewDosAndDonts from "./overview/BrandFormTabOverviewDosAndDonts.vue";
import BrandFormTabOverviewEmptyState from "./overview/BrandFormTabOverviewEmptyState.vue";

const store = useBrandFormStore();

// Identity sections that have data
type IdentitySection = {
  key: "about-us" | "mission" | "vision" | "values" | "tone-of-voice";
  type: "text" | "chips";
  value: string | string[];
};

const identitySections = computed<IdentitySection[]>(() => {
  const sections: IdentitySection[] = [];
  const identity = store.brand.identity;

  if (identity.about_us?.value) {
    sections.push({
      key: "about-us",
      type: "text",
      value: identity.about_us.value,
    });
  }

  if (identity.mission?.value) {
    sections.push({
      key: "mission",
      type: "text",
      value: identity.mission.value,
    });
  }

  if (identity.vision?.value) {
    sections.push({
      key: "vision",
      type: "text",
      value: identity.vision.value,
    });
  }

  if (identity.values?.value?.length) {
    sections.push({
      key: "values",
      type: "chips",
      value: identity.values.value,
    });
  }

  if (identity.tone_voice?.value?.length) {
    sections.push({
      key: "tone-of-voice",
      type: "chips",
      value: identity.tone_voice.value,
    });
  }

  return sections;
});

const logos = computed(() =>
  Array.isArray(store.brand.logos)
    ? store.brand.logos
    : store.brand.logos.values,
);

const colors = computed(() => {
  const colors = Array.isArray(store.brand.colors)
    ? store.brand.colors
    : store.brand.colors.values;

  return colors.map((apiColor: BrandColor) => ({
    id: apiColor.id,
    name: apiColor.name,
    hex: apiColor.hex_code,
    category: apiColor.category,
    source: apiColor.source,
  }));
});

const typographies = computed(() =>
  Array.isArray(store.brand.typography)
    ? store.brand.typography
    : store.brand.typography.values,
);

const tabsContext = useTabsContext();

const handleAddIdentity = () => {
  if (tabsContext) {
    tabsContext.current.value = "identity";
  }
};

const handleAddColors = () => {
  if (tabsContext) {
    tabsContext.current.value = "colors";
  }
};

const handleAddLogos = () => {
  if (tabsContext) {
    tabsContext.current.value = "logos";
  }
};

const handleAddTypography = () => {
  if (tabsContext) {
    tabsContext.current.value = "typography";
  }
};

const handleAddDosAndDonts = () => {
  if (tabsContext) {
    tabsContext.current.value = "dosAndDonts";
  }
};

const colorsByCategories = computed(() => {
  if (!colors.value.length) return {};

  const result: Partial<Record<BrandFormColorCategory, BrandFormColor[]>> = {};

  for (const category of brandFormColorCategories) {
    const categoryColors = colors.value.filter(
      (color) => color.category === category,
    );
    if (categoryColors.length > 0) {
      result[category] = categoryColors;
    }
  }

  return result;
});

const categoryEntries = computed(() => {
  return Object.entries(colorsByCategories.value);
});

const dosRules = computed(() => {
  return Array.isArray(store.brand.dos_donts)
    ? store.brand.dos_donts.filter((rule) => rule.type === "do")
    : [];
});

const dontsRules = computed(() => {
  return Array.isArray(store.brand.dos_donts)
    ? store.brand.dos_donts.filter((rule) => rule.type === "dont")
    : [];
});
</script>

<template>
  <BrandFormTabLayout is="div">
    <AccordionList variant="card">
      <Accordion openByDefault>
        <template #title>
          <strong>{{ $t("brands.settings.identity.title") }}</strong>
        </template>

        <div
          v-if="identitySections.length"
          class="tw:flex tw:flex-col tw:gap-5"
        >
          <template
            v-for="(section, index) in identitySections"
            :key="section.key"
          >
            <div>
              <h4 class="tw:mb-2 tw:font-bold">
                {{ $t(`brands.settings.identity.${section.key}.label`) }}
              </h4>

              <!-- Text content -->
              <p v-if="section.type === 'text'">{{ section.value }}</p>

              <!-- Chips content -->
              <ChipList v-else-if="section.type === 'chips'">
                <Chip
                  v-for="item in section.value"
                  :key="item"
                  variant="label"
                  color="secondary"
                >
                  {{ item }}
                </Chip>
              </ChipList>
            </div>

            <Separator v-if="index < identitySections.length - 1" />
          </template>
        </div>

        <BrandFormTabOverviewEmptyState v-else @add="handleAddIdentity">
          {{ $t("brands.settings.overview.identity.empty-state") }}
        </BrandFormTabOverviewEmptyState>
      </Accordion>

      <Accordion>
        <template #title>
          <strong>{{ $t("brands.settings.colors.title") }}</strong>
        </template>

        <div v-if="colors.length > 0" class="tw:flex tw:flex-col tw:gap-5">
          <template v-for="(entry, index) in categoryEntries">
            <div>
              <h4 class="tw:mb-2 tw:font-bold">
                {{ $t(`brands.settings.colors.categories.${entry[0]}`) }}
              </h4>

              <div
                class="tw:grid tw:gap-2 tw:sm:grid-cols-2 tw:md:grid-cols-3 tw:lg:grid-cols-5"
              >
                <BrandFormTabOverviewColor
                  v-for="color in entry[1]"
                  :color="color"
                />
              </div>
            </div>

            <Separator v-if="index < categoryEntries.length - 1" />
          </template>
        </div>

        <BrandFormTabOverviewEmptyState v-else @add="handleAddColors">
          {{ $t("brands.settings.overview.colors.empty-state") }}
        </BrandFormTabOverviewEmptyState>
      </Accordion>

      <Accordion>
        <template #title>
          <strong>{{ $t("brands.settings.logos.title") }}</strong>
        </template>

        <div
          v-if="logos.length > 0"
          class="tw:grid tw:gap-6 tw:md:grid-cols-2 tw:lg:grid-cols-3"
        >
          <BrandFormTabOverviewLogo v-for="logo in logos" :logo="logo" />
        </div>

        <BrandFormTabOverviewEmptyState v-else @add="handleAddLogos">
          {{ $t("brands.settings.overview.logos.empty-state") }}
        </BrandFormTabOverviewEmptyState>
      </Accordion>

      <Accordion>
        <template #title>
          <strong>{{ $t("brands.settings.typography.title") }}</strong>
        </template>

        <div
          v-if="typographies.length > 0"
          style="max-width: 824px"
          class="tw:grid tw:gap-6"
        >
          <div
            v-for="typography in typographies"
            class="tw:grid tw:gap-6 tw:lg:grid-cols-4"
          >
            <BrandFormTabOverviewTypography :typography="typography" />
          </div>
        </div>

        <BrandFormTabOverviewEmptyState v-else @add="handleAddTypography">
          {{ $t("brands.settings.overview.typography.empty-state") }}
        </BrandFormTabOverviewEmptyState>
      </Accordion>

      <Accordion>
        <template #title>
          <strong>{{ $t("brands.settings.dos-and-donts.title") }}</strong>
        </template>

        <div
          v-if="
            Array.isArray(store.brand.dos_donts) &&
            store.brand.dos_donts.length > 0
          "
          class="tw:flex tw:flex-col tw:gap-6"
        >
          <!-- Do's Section -->
          <div>
            <div class="tw:mb-2 tw:flex tw:items-center tw:gap-2">
              <Icon
                icon="tabler:circle-check-filled"
                class="tw:text-xl tw:text-success-500"
              />
              <h4 class="tw:font-semibold">
                {{ $t("brands.settings.dos-and-donts.dos") }}
              </h4>
            </div>

            <div
              v-if="dosRules.length > 0"
              class="tw:flex tw:flex-col tw:gap-3"
            >
              <BrandFormTabOverviewDosAndDonts
                v-for="rule in dosRules"
                :key="rule.id"
                :rule="rule"
              />
            </div>
            <p v-else class="tw:text-sm tw:text-gray-500">
              {{ $t("brands.settings.dos-and-donts.no-rules-added") }}
            </p>
          </div>

          <Separator />

          <!-- Don'ts Section -->
          <div>
            <div class="tw:mb-2 tw:flex tw:items-center tw:gap-2">
              <Icon
                icon="tabler:circle-x-filled"
                class="tw:text-xl tw:text-error-500"
              />
              <h4 class="tw:font-semibold">
                {{ $t("brands.settings.dos-and-donts.donts") }}
              </h4>
            </div>

            <div
              v-if="dontsRules.length > 0"
              class="tw:flex tw:flex-col tw:gap-3"
            >
              <BrandFormTabOverviewDosAndDonts
                v-for="rule in dontsRules"
                :key="rule.id"
                :rule="rule"
              />
            </div>
            <p v-else class="tw:text-sm tw:text-gray-500">
              {{ $t("brands.settings.dos-and-donts.no-rules-added") }}
            </p>
          </div>
        </div>

        <BrandFormTabOverviewEmptyState v-else @add="handleAddDosAndDonts">
          {{ $t("brands.settings.overview.dos-and-donts.empty-state") }}
        </BrandFormTabOverviewEmptyState>
      </Accordion>
    </AccordionList>

    <template #actions>
      <BrandFormGoToWorkspaceButton />
    </template>
  </BrandFormTabLayout>
</template>
