<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });

const physicalTips = [
  "real-environment",
  "scale-reference",
  "macro-details",
  "packaging",
  "in-use",
] as const;

const serviceTips = [
  "tools",
  "customer-interaction",
  "certificates",
  "before-after",
  "branded-merchandise",
] as const;
</script>

<template>
  <ModalGeneric v-model="isOpen" scrollable="inner">
    <template #title>{{ $t("products.image.helpful-details.title") }}</template>

    <template #description>
      {{ $t("products.image.helpful-details.description") }}
    </template>

    <div class="tw:flex tw:flex-col tw:gap-8">
      <section class="tw:flex tw:flex-col tw:gap-4">
        <h3 class="tw:font-bold tw:text-gray-900">
          {{ $t("products.image.helpful-details.physical-heading") }}
        </h3>

        <ul
          class="tw:list-disc tw:space-y-5 tw:pl-5 tw:font-medium tw:text-gray-700 tw:marker:text-primary"
        >
          <li v-for="tip in physicalTips" :key="tip">
            <i18n-t :keypath="`products.image.helpful-details.physical.${tip}`">
              <template #label>
                <strong class="tw:text-primary">{{
                  $t(`products.image.helpful-details.physical.${tip}-label`)
                }}</strong>
              </template>
            </i18n-t>
          </li>
        </ul>
      </section>

      <section class="tw:flex tw:flex-col tw:gap-4">
        <h3 class="tw:font-bold tw:text-gray-900">
          {{ $t("products.image.helpful-details.service-heading") }}
        </h3>

        <ul
          class="tw:list-disc tw:space-y-5 tw:pl-5 tw:font-medium tw:text-gray-700 tw:marker:text-primary"
        >
          <li v-for="tip in serviceTips" :key="tip">
            <i18n-t :keypath="`products.image.helpful-details.service.${tip}`">
              <template #label>
                <strong class="tw:text-primary">{{
                  $t(`products.image.helpful-details.service.${tip}-label`)
                }}</strong>
              </template>
            </i18n-t>
          </li>
        </ul>
      </section>
    </div>

    <template #continue>
      {{ $t("products.image.helpful-details.continue") }}
    </template>
  </ModalGeneric>
</template>
