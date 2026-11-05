<template>
  <div class="tw:flex tw:flex-col tw:items-start tw:gap-3">
    <IconCard icon="tabler-star" variant="gray" />
    <h3 class="tw:text-lg tw:font-extrabold tw:text-black">
      <slot name="title" />
    </h3>
    <LandingPageParagraph>
      <slot />
    </LandingPageParagraph>
  </div>
</template>
