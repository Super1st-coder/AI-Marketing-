import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ButtonDropdown from "@/components/buttons/base/ButtonDropdown.vue";
import ButtonDropdownOption from "@/components/buttons/base/ButtonDropdownOption.vue";

const meta: Meta<typeof ButtonDropdown> = {
  title: "Components/Dropdowns/ButtonDropdown",
  component: ButtonDropdown,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: [
        "default",
        "placement",
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
    placement: {
      control: "select",
      options: [
        "bottom",
        "bottom-end",
        "bottom-start",
        "left",
        "left-end",
        "left-start",
        "right",
        "right-end",
        "right-start",
        "top",
        "top-end",
        "top-start",
      ],
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
    placement: "bottom",
    color: "default",
    variant: "solid",
    size: "lg",
    disabled: false,
    isLoading: false,
  },
  render: (args) => ({
    components: { ButtonDropdown, ButtonDropdownOption },
    setup() {
      return { args };
    },
    template: `
      <ButtonDropdown v-bind="args">
        {{ args.default }}
        <template #options>
          <ButtonDropdownOption>Simple option</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-calendar">Option with icon</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-calendar" color="primary">Option 3</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-check" color="success">Option 4</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-check" color="success" disabled>Disabled option</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-check" color="success" disabled>Disabled option</ButtonDropdownOption>
        </template>
      </ButtonDropdown>`,
  }),
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    default: "Primary",
    color: "primary",
    icon: "tabler-chevron-down",
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
    icon: "tabler-chevron-down",
  },
};

export const BothIcons: Story = {
  args: {
    default: "Sort by",
    color: "primary",
    leftIcon: "tabler-search",
    icon: "tabler-chevron-down",
    variant: "label",
  },
};

export const CustomColorExample: Story = {
  args: {
    default: "Whatsapp",
    color: "primary",
    customColor: "#25d366",
    leftIcon: "tabler-brand-whatsapp",
    icon: "tabler-chevron-down",
  },
  parameters: {
    controls: {
      exclude: ["color"],
    },
  },
};
