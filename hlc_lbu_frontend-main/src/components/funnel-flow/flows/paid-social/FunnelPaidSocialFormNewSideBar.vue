<script setup lang="ts">
import { SidebarLinkColor } from "@/components/navigation/SidebarLink.vue";

export type FunnelFlowSidebarSubMenuItem = {
  id: number | string;
  label: string;
  icon?: string;
  selected?: boolean;
  disabled?: boolean;
  variant?: SidebarLinkColor;
  hasAlert?: boolean;
  hasSuccess?: boolean;
  click?: () => void;
};

export type FunnelFlowSidebarMenuItem = {
  id: number | string;
  label: string;
  icon?: string;
  selected?: boolean;
  disabled?: boolean;
  variant?: SidebarLinkColor;
  open?: boolean;
  hasAlert?: boolean;
  hasSuccess?: boolean;
  children?: FunnelFlowSidebarSubMenuItem[];
  click?: () => void;
};

withDefaults(
  defineProps<{
    items: FunnelFlowSidebarMenuItem[];
  }>(),
  {
    items: () => [],
  },
);
</script>

<template>
  <div class="tw:flex tw:w-full tw:flex-col tw:md:flex-row">
    <div
      class="tw:sticky tw:flex tw:w-full tw:shrink-0 tw:flex-col tw:gap-2 tw:self-start tw:overflow-y-auto tw:border-b tw:border-gray-300 tw:bg-white tw:px-3 tw:py-6 tw:md:top-[66px] tw:md:h-[calc(100vh-66px)] tw:md:max-w-[260px] tw:md:border-r tw:md:border-b-0"
    >
      <div v-for="parent in items">
        <SidebarLink
          :icon="parent.icon"
          :hasAlert="parent.hasAlert"
          :hasSuccess="parent.hasSuccess"
          :disabled="parent.disabled"
          :selected="parent.selected"
          @click="
            async () => {
              if (parent.click) {
                if ((await useSaveLockingStore().execute()) === 'cancel')
                  return;

                parent.click();
              }
            }
          "
          :expandable="false"
          :variant="parent.open ? 'primary' : undefined"
        >
          {{ parent.label }}

          <template v-if="parent.children && parent.children.length > 0" #after>
            <Icon
              :icon="
                parent.open ? 'tabler-chevron-down' : 'tabler-chevron-right'
              "
              class="tw:shrink-0 tw:text-lg tw:text-primary-text"
            />
          </template>
        </SidebarLink>

        <ul v-show="parent.open">
          <SidebarLink
            v-for="child in parent.children"
            :icon="child.icon"
            :hasAlert="child.hasAlert"
            :hasSuccess="child.hasSuccess"
            :disabled="child.disabled"
            :selected="child.selected"
            @click="
              async () => {
                if (child.click) {
                  if ((await useSaveLockingStore().execute()) === 'cancel')
                    return;
                  child.click();
                }
              }
            "
            class="tw:pl-10"
            :expandable="false"
          >
            {{ child.label }}
          </SidebarLink>
        </ul>
      </div>
    </div>

    <div class="tw:grow">
      <slot />
    </div>
  </div>
</template>
