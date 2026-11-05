<script lang="ts" setup>
const store = useMenusStore();
</script>

<template>
  <!-- Desktop -->
  <aside
    class="tw:sticky tw:top-[66px] tw:hidden tw:h-[calc(100vh-66px)] tw:shrink-0 tw:self-start tw:overflow-y-auto tw:border-r tw:border-gray-300 tw:bg-white tw:md:block"
    :class="{
      'tw:w-[225px] tw:lg:w-[288px]': store.isMenuVisuallyExpanded,
    }"
  >
    <nav class="tw:flex tw:h-full tw:flex-col">
      <!-- Header -->
      <div class="tw:sticky tw:top-0 tw:bg-white">
        <div
          class="tw:flex tw:justify-between tw:px-6 tw:py-5"
          :class="{
            'tw:gap-1': store.isMenuVisuallyExpanded,
          }"
        >
          <!-- Header content -->
          <div>
            <slot name="header" />
          </div>

          <div
            class="tw:flex"
            :class="{
              'tw:justify-center': !store.isMenuVisuallyExpanded,
              'tw:justify-end': store.isMenuVisuallyExpanded,
            }"
          >
            <SidebarToggleButton />
          </div>
        </div>

        <Separator />
      </div>

      <!-- Body and footer -->
      <div class="tw:flex tw:grow tw:flex-col tw:gap-5 tw:px-3 tw:py-6">
        <!-- Body -->
        <slot />

        <!-- Footer -->
        <div v-if="$slots.footer" class="tw:flex tw:grow tw:items-end">
          <slot name="footer" />
        </div>
      </div>
    </nav>
  </aside>

  <!-- Mobile -->
  <div
    class="tw:fixed tw:top-[66px] tw:z-10 tw:h-[calc(100%-66px)] tw:w-full tw:transition-opacity tw:md:hidden"
    :class="{
      'tw:pointer-events-none': !store.isMenuOpen,
    }"
  >
    <div
      class="tw:absolute tw:inset-0 tw:w-full tw:bg-black/50 tw:transition-all"
      :class="{
        'tw:opacity-0': !store.isMenuOpen,
        'tw:opacity-100': store.isMenuOpen,
      }"
      @click="store.closeMenu"
    ></div>

    <aside
      class="tw:relative tw:h-full tw:w-[250px] tw:shrink-0 tw:overflow-y-auto tw:bg-white tw:transition-all"
      :class="{
        'tw:left-[-250px]': !store.isMenuOpen,
        'tw:left-0': store.isMenuOpen,
      }"
    >
      <nav class="tw:flex tw:h-full tw:flex-col">
        <!-- Header -->
        <div class="tw:px-6 tw:py-5">
          <slot name="header" />
        </div>

        <Separator />

        <!-- Body and footer -->
        <div class="tw:flex tw:grow tw:flex-col tw:gap-5 tw:px-3 tw:py-6">
          <!-- Body -->
          <slot />

          <!-- Footer -->
          <div v-if="$slots.footer" class="tw:flex tw:grow tw:items-end">
            <slot name="footer" />
          </div>
        </div>
      </nav>
    </aside>
  </div>
</template>
