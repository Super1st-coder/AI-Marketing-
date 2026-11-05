import { breakpointsTailwind } from "@vueuse/core";
import { defineStore } from "pinia";

export const useMenusStore = defineStore("MenusStore", () => {
  const isMenuOpen = ref(false);
  const isMenuExpanded = ref(true);
  const route = useRoute();

  const breakpoints = useBreakpoints(breakpointsTailwind);
  const isDesktop = breakpoints.greaterOrEqual("md");

  const toggleMenu = () => {
    isMenuOpen.value = !isMenuOpen.value;
  };

  const toggleMenuExpanded = () => {
    isMenuExpanded.value = !isMenuExpanded.value;
  };

  const closeMenu = () => {
    isMenuOpen.value = false;
  };

  const openMenu = () => {
    isMenuOpen.value = true;
  };

  const isMenuVisuallyExpanded = computed(() =>
    isDesktop.value ? isMenuExpanded.value : true,
  );

  // Close the menu when the route changes
  watch(
    () => route.fullPath,
    () => {
      closeMenu();
    },
  );

  return {
    isMenuOpen,
    isMenuExpanded,
    toggleMenu,
    closeMenu,
    openMenu,
    toggleMenuExpanded,
    isMenuVisuallyExpanded,
  };
});
