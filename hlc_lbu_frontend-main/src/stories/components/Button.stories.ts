import type { Meta, StoryObj } from "@storybook/vue3-vite";
import Button from "@/components/buttons/base/Button.vue";

const meta: Meta<typeof Button> = {
  title: "Components/Button",
  component: Button,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: [
        "default",
        "color",
        "variant",
        "size",
        "disabled",
        "isLoading",
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
      options: ["sm", "md", "lg"],
    },
    disabled: {
      control: "boolean",
    },
    isLoading: {
      control: "boolean",
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
    size: "lg",
    disabled: false,
    isLoading: false,
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
    default: "Go Back",
    color: "primary",
    leftIcon: "tabler-calendar",
  },
};

export const RightIcon: Story = {
  args: {
    default: "Button",
    color: "primary",
    icon: "tabler-search",
  },
};

export const BothIcons: Story = {
  args: {
    default: "Button",
    color: "primary",
    leftIcon: "tabler-calendar",
    icon: "tabler-search",
  },
};

export const CustomColorExample1: Story = {
  args: {
    default: "Whatsapp",
    color: "primary",
    customColor: "#25d366",
    leftIcon: "tabler-brand-whatsapp",
  },
  parameters: {
    controls: {
      exclude: ["color"],
    },
  },
};

export const CustomColorExample2: Story = {
  args: {
    default: "LinkedIn",
    color: "primary",
    customColor: "#0e76a8",
    leftIcon: "tabler-brand-linkedin",
  },
  parameters: {
    controls: {
      exclude: ["color"],
    },
  },
};
