<script setup lang="ts">
import { isVisualGenerationPending } from "@/services/funnel-flow/paid-social/AdsApi";
import { abyssaleGenerationErrorKey } from "./composables/useGenerateAbyssaleVisuals";

const { t } = useI18n();

const generationErrorMessage = inject(abyssaleGenerationErrorKey);

const store = useFunnelPaidSocialAdsAssemblyStore();

const isWaitingForAbyssale = computed(() => {
  if (!store.currentVariant) {
    return false;
  }

  return isVisualGenerationPending(store.currentVariant.media);
});

const abyssaleFormatsWithErrors = computed(
  () =>
    store.currentVariant?.media.formats?.filter((template) =>
      template.errors ? template.errors.length > 0 : false,
    ) ?? [],
);

const displayAbyssaleErrors = computed(
  () => abyssaleFormatsWithErrors.value.length > 0,
);

const textFittingSolutionMessage = computed(() => {
  const formatsWithTextFittingErrors = abyssaleFormatsWithErrors.value
    .filter((format) =>
      format.errors?.some((error) =>
        error.includes("cannot fit within the defined space"),
      ),
    )
    .map((format) => `Format ${format.id}`);

  if (formatsWithTextFittingErrors.length === 0) return undefined;

  return t(
    "funnel-flow.paid-social.ads.refine.editor.abyssale-error.text-auto-resize-solution",
    {
      formats: formatsWithTextFittingErrors.join(", "),
    },
  );
});
</script>

<template>
  <Alert v-if="generationErrorMessage" type="error" autoScroll>
    {{ generationErrorMessage }}
  </Alert>

  <!-- Abyssale errors -->
  <Alert v-if="displayAbyssaleErrors" type="error" autoScroll>
    <template #custom>
      <p>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.abyssale-error.data-couldnt-be-sent",
          )
        }}<br /><br />
      </p>

      <template v-for="format in abyssaleFormatsWithErrors">
        <i18n-t
          keypath="funnel-flow.paid-social.ads.refine.editor.abyssale-error.format"
          tag="p"
        >
          <template #id>
            <strong>{{ format.id }}</strong>
          </template>
        </i18n-t>

        <ul class="tw:list-disc">
          <li v-for="error in format.errors" class="tw:ml-4">
            {{ error }}
          </li>
        </ul>

        <br />
      </template>

      <p v-if="textFittingSolutionMessage">
        {{ textFittingSolutionMessage }}
      </p>
    </template>
  </Alert>

  <!-- Abyssale warning -->
  <Alert v-if="isWaitingForAbyssale" type="warning" autoScroll>
    {{
      $t(
        "funnel-flow.paid-social.ads.refine.editor.processing-and-sending-to-abyssale",
      )
    }}
  </Alert>
</template>
