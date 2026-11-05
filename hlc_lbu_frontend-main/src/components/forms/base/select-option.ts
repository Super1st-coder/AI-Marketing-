import type { ChipProps } from "@/components/chips/Chip.vue";

export type SelectOptionChip = Omit<ChipProps, "size"> & {
  label: string;
};

export type SelectOption = {
  type?: "item" | "subheader" | "divider";
  value?: unknown;
  label?: string;
  group?: string;
  image?: string;
  icon?: string;
  iconClass?: string;
  subtitle?: string;
  disabled?: boolean;
  chip?: SelectOptionChip;
};

export function toVuetifySelectItems(options: SelectOption[]): SelectOption[] {
  const items: SelectOption[] = [];
  let lastGroup: string | undefined;

  for (const option of options) {
    if (option.type === "subheader") {
      items.push({ type: "subheader", label: option.label });
      lastGroup = undefined;
      continue;
    }

    if (option.type === "divider") {
      items.push({ type: "divider" });
      lastGroup = undefined;
      continue;
    }

    if (option.group && option.group !== lastGroup) {
      items.push({ type: "subheader", label: option.group });
      lastGroup = option.group;
    } else if (!option.group) {
      lastGroup = undefined;
    }

    const { group: _group, ...item } = option;
    items.push(item);
  }

  return items;
}
