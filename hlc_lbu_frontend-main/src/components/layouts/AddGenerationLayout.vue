<template>
  <TopNav>
    <Button
      v-if="!$route.path.includes('getting-started')"
      variant="outlined"
      leftIcon="tabler-arrow-left"
      :to="{ name: 'AdGenerationGettingStarted' }"
    >
      START NEW HYPOTHESIS
    </Button>
  </TopNav>

  <GradientBackground>
    <RouterView v-slot="{ Component, route }">
      <Suspense :key="route.path">
        <Container class="tw:min-h-[calc(100vh-66px)] tw:py-10 tw:lg:py-[88px]">
          <component :is="Component"></component>
        </Container>

        <template #fallback>
          <CircleLoaderDefault class="tw:min-h-[calc(100vh-66px)]" />
        </template>
      </Suspense>
    </RouterView>
  </GradientBackground>
</template>
