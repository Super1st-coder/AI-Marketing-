<template>
  <div
    class="tw:self-start tw:overflow-hidden tw:rounded-3xl tw:bg-white tw:shadow-lg"
  >
    <div
      class="tw:flex tw:items-center tw:gap-4 tw:bg-[#005246] tw:px-6 tw:py-3 tw:text-white"
    >
      <div class="tw:shrink-0 tw:rounded-full tw:bg-white tw:p-2">
        <Icon icon="tabler-building" class="tw:text-primary-text" />
      </div>

      <h2 class="tw:text-lg tw:font-extrabold">Chatbot</h2>
    </div>

    <div class="tw:p-2">
      <slot />
    </div>
  </div>
</template>
