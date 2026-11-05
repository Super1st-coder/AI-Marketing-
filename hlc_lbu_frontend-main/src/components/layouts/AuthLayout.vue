<template>
  <GradientBackground>
    <Container>
      <main
        class="tw:flex tw:min-h-screen tw:items-center tw:justify-center tw:py-16"
      >
        <div class="tw:relative tw:max-w-[460px] tw:grow tw:contain-layout">
          <img
            class="tw:absolute tw:-top-14 tw:-left-11"
            src="/images/top-shape.svg"
            alt=""
            role="presentation"
          />
          <img
            class="tw:absolute tw:-right-14 tw:-bottom-14"
            src="/images/bottom-shape.svg"
            alt=""
            role="presentation"
          />

          <div class="tw:relative">
            <slot />
          </div>
        </div>
      </main>
    </Container>
  </GradientBackground>
</template>
