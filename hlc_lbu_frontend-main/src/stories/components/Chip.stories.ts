import type { Meta, StoryObj } from "@storybook/vue3-vite";
import Chip from "@/components/chips/Chip.vue";

const meta: Meta<typeof Chip> = {
  title: "Components/Chip",
  component: Chip,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: [
        "default",
        "color",
        "variant",
        "size",
        "icon",
        "leftIcon",
        "customColor",
      ],
    },
  },
  argTypes: {
    default: {
      control: "text",
    },
    color: {
      control: "select",
      options: ["primary", "secondary", "success", "error", "warning", "info"],
    },
    variant: {
      control: "select",
      options: ["solid", "outlined", "text", "label"],
    },
    size: {
      control: "select",
      options: ["sm", "md"],
    },
    icon: {
      control: "text",
      description: "Iconify code. Example: **tabler-calendar**",
    },
    leftIcon: {
      control: "text",
      description: "Iconify code. Example: **tabler-calendar**",
    },
    customColor: {
      control: "color",
    },
  },

  args: {
    default: "Button",
    color: "default",
    variant: "solid",
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    default: "Primary",
    color: "primary",
  },
};

export const Secondary: Story = {
  args: {
    default: "Secondary",
    color: "secondary",
  },
};

export const Success: Story = {
  args: {
    default: "Success",
    color: "success",
  },
};

export const Warning: Story = {
  args: {
    default: "Warning",
    color: "warning",
  },
};

export const Error: Story = {
  args: {
    default: "Error",
    color: "error",
  },
};

export const Info: Story = {
  args: {
    default: "Info",
    color: "info",
  },
};

export const Outlined: Story = {
  args: {
    default: "Outlined",
    color: "primary",
    variant: "outlined",
  },
};

export const Label: Story = {
  args: {
    default: "Label",
    color: "primary",
    variant: "label",
  },
};

export const Text: Story = {
  args: {
    default: "Text",
    color: "primary",
    variant: "text",
  },
};

export const LeftIcon: Story = {
  args: {
    default: "Ready to use",
    variant: "label",
    color: "success",
    leftIcon: "tabler-check",
  },
};
