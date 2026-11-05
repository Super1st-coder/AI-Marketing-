<template>
  <Card
    padding="lg"
    class="tw:h-full tw:p-0! tw:shadow-[0px_8px_16px] tw:shadow-primary-text/8"
  >
    <div class="tw:flex tw:items-center tw:gap-2 tw:px-3 tw:py-4">
      <EmailButton icon="tabler-chevron-left" type="button" />

      <div class="tw:grow">
        <h3 class="tw:text-[15px]">
          <slot name="subjectLine" />
        </h3>
        <p
          v-if="$slots.previewText"
          class="tw:text-sm tw:text-secondary-text/50"
        >
          <slot name="previewText" />
        </p>
      </div>

      <EmailButton icon="tabler-chevron-left" class="tw:ml-2.5" type="button" />
      <EmailButton icon="tabler-chevron-right" type="button" />
    </div>

    <Separator />

    <div class="tw:flex tw:items-center tw:p-6">
      <img
        src="/images/dummy-avatar.png"
        alt=""
        class="tw:mr-4 tw:h-[38px] tw:w-[38px] tw:shrink-0"
      />

      <div class="tw:grow">
        <h4 class="tw:text-[15px]">Milena Osgarby</h4>
        <p class="tw:text-[13px] tw:text-secondary-text">
          milena.osgarby@gmail.com
        </p>
      </div>

      <div>
        <EmailButton icon="tabler-paperclip" type="button" />
        <EmailButton icon="tabler-star" type="button" />
        <EmailButton icon="tabler-dots-vertical" type="button" />
      </div>
    </div>

    <Separator />

    <div class="tw:p-6 tw:text-secondary-text">
      <slot />
    </div>
  </Card>
</template>
