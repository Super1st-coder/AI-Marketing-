import { SidebarLinkColor } from "@/components/navigation/SidebarLink.vue";

export type ImageLibrarySource = {
  slug: string;
  label: string;
  icon: string;
  color?: SidebarLinkColor;
  cropper: boolean;
  component?: Component;
};
