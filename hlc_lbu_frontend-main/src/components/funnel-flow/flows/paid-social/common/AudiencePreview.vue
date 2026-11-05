<script setup lang="ts">
import { AudienceItem, Country } from "@/services/projects/AudienceApi";

const props = defineProps<{
  audience: AudienceItem;
  audienceType?: "preferred" | "generated" | "ads-experiment" | "saved";
  displayActions?: boolean;
  showTitle?: boolean;
}>();

const emit = defineEmits<{ removeComment: [audience: AudienceItem] }>();
const { t, te } = useI18n();

const ageList = computed<string[]>(() =>
  Array.isArray(props.audience.age)
    ? props.audience.age
    : props.audience.age
      ? [props.audience.age]
      : [],
);

const locationList = computed<Country[] | string[]>(() =>
  Array.isArray(props.audience.location)
    ? props.audience.location
    : props.audience.location
      ? [props.audience.location]
      : [],
);

const genderLabel = computed(() => {
  const gender = props.audience.gender.toLowerCase();
  const key = `funnel-flow.paid-social.audience.create-audience-modal.fields.gender.options.${gender}`;
  return te(key) ? t(key) : props.audience.gender;
});

function getLocation(location: Country | string) {
  if (typeof location === "string") {
    return location;
  } else {
    return [
      location.longName,
      location.state,
      location.name,
      location.neighborhood,
    ]
      .filter((v) => v && v.trim())
      .join(", ");
  }
}
</script>

<template>
  <div
    class="tw:flex tw:flex-1 tw:flex-col tw:gap-4 tw:rounded-xl tw:bg-white tw:p-5 tw:text-sm"
  >
    <h3 v-if="props.showTitle" class="tw:font-bold">
      {{ props.audience.name }}
    </h3>

    <div>{{ props.audience.description }}</div>

    <Separator />

    <ul>
      <li class="tw:mb-4 tw:flex tw:justify-between tw:gap-5">
        <span>
          {{
            $t("funnel-flow.paid-social.audience.audience-info.labels.gender")
          }}
        </span>

        <span class="tw:text-right"> {{ genderLabel }} </span>
      </li>
      <li class="tw:mb-4 tw:flex tw:justify-between tw:gap-5">
        <span>
          {{ $t("funnel-flow.paid-social.audience.audience-info.labels.age") }}
        </span>

        <ul>
          <li v-for="age in ageList" :key="age" class="tw:text-right">
            {{ age }}
          </li>
        </ul>
      </li>
      <li class="tw:mb-4 tw:flex tw:justify-between tw:gap-5">
        <span>
          {{
            $t("funnel-flow.paid-social.audience.audience-info.labels.location")
          }}
        </span>

        <ul>
          <li
            class="tw:text-right"
            v-for="location in locationList"
            :key="typeof location === 'string' ? location : location.shortName"
          >
            {{ getLocation(location) }}
          </li>
        </ul>
      </li>
      <li class="tw:flex tw:justify-between tw:gap-5">
        <span>
          {{
            $t("funnel-flow.paid-social.audience.audience-info.labels.income")
          }}
        </span>

        <span class="tw:text-right"> {{ props.audience.income }} </span>
      </li>
    </ul>

    <Separator />

    <div>
      <h3 class="tw:mb-4 tw:text-sm">
        {{
          $t("funnel-flow.paid-social.audience.audience-info.labels.interest")
        }}
      </h3>

      <div class="tw:flex tw:flex-wrap tw:gap-2">
        <button
          v-for="interest in props.audience.interests"
          :key="interest"
          class="tw:rounded-full tw:bg-primary/30 tw:px-4 tw:py-2 tw:text-sm"
        >
          {{ interest }}
        </button>
      </div>
    </div>

    <template
      v-if="props.audienceType === 'preferred' && props.audience.comments"
    >
      <Separator />

      <div>
        <div class="tw:flex tw:items-start">
          <div class="tw:flex-1">
            <h3 class="tw:mb-4 tw:text-sm">
              {{
                $t(
                  "funnel-flow.paid-social.audience.audience-info.labels.comment",
                )
              }}
            </h3>
            <p>
              {{ props.audience.comments }}
            </p>
          </div>

          <button
            v-if="displayActions"
            @click="emit('removeComment', props.audience)"
          >
            <Icon icon="tabler-trash" class="text-error tw:text-lg" />
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style></style>
