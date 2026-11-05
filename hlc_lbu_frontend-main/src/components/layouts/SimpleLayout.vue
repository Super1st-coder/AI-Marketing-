<template>
  <TopNav />

  <div class="tw:flex tw:min-h-[calc(100vh-66px)]">
    <GradientBackground class="tw:w-full">
      <main class="tw:h-full">
        <RouterView v-slot="{ Component }">
          <Suspense suspensible :timeout="0">
            <component :is="Component"></component>

            <template #fallback>
              <CircleLoaderDefault class="tw:h-full" />
            </template>
          </Suspense>
        </RouterView>
      </main>
    </GradientBackground>
  </div>
</template>
