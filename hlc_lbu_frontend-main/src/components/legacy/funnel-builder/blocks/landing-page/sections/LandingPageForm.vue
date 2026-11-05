<script lang="ts" setup>
import { LandingPage } from "@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page/landing-page.vue";
import { useFormValues } from "vee-validate";

const { value: values } = useFormValues<LandingPage>();

useMaxHeightCards([".form-title", ".form-form", ".form-cta"], [values]);

const name = ref<string | undefined>(undefined);
const lastName = ref<string | undefined>(undefined);
const email = ref<string | undefined>(undefined);
const phone = ref<string | undefined>(undefined);
</script>

<template>
  <LandingColumn>
    <template #guidelines>
      <LandingPageGuideline class="form-title">
        <template #title> Form Title </template>

        Add more context to the headline. Explain how the product solves a
        problem or offers a unique benefit.
      </LandingPageGuideline>

      <div class="form-form tw:hidden tw:lg:block"></div>

      <LandingPageGuideline class="form-cta">
        <template #title> Form CTA </template>

        Use action-oriented text to get the user to apply.
      </LandingPageGuideline>
    </template>

    <LandingPageTitle class="form-title">
      {{ values.formTitle }}
    </LandingPageTitle>

    <div class="form-form tw:flex tw:w-full tw:flex-col tw:gap-5">
      <FieldBaseText
        placeholder="Name"
        disabled
        class="tw:pointer-events-none"
        v-model="name"
      />
      <FieldBaseText
        placeholder="Last Name"
        disabled
        class="tw:pointer-events-none"
        v-model="lastName"
      />
      />
      <FieldBaseText
        placeholder="Email"
        disabled
        class="tw:pointer-events-none"
        v-model="email"
      />
      <FieldBaseText
        placeholder="Phone"
        disabled
        class="tw:pointer-events-none"
        v-model="phone"
      />
    </div>

    <div class="form-cta">
      <LandingPageCta>
        {{ values.formCta }}
      </LandingPageCta>
    </div>

    <template #modalTitle> Form section </template>
    <template #modalBody>
      <EditableCardSection
        name="formTitle"
        title="Form Title"
        icon="tabler-pennant"
        iconVariant="primary"
        editable
      />

      <EditableCardSection
        name="formCta"
        title="Form CTA"
        icon="tabler-social"
        iconVariant="info"
        editable
      />
    </template>
  </LandingColumn>
</template>
