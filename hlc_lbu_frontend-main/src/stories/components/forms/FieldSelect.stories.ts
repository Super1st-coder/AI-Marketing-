import type { Meta, StoryObj } from "@storybook/vue3-vite";
import FieldSelect from "@/components/forms/base/FieldSelect.vue";

const meta: Meta<typeof FieldSelect> = {
  title: "Components/Forms/FieldSelect",
  component: FieldSelect,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: [
        "options",
        "label",
        "placeholder",
        "description",
        "orientation",
        "disabled",
        "required",
      ],
    },
  },
  argTypes: {
    options: {
      control: "object",
    },
    label: {
      control: "text",
    },
    placeholder: {
      control: "text",
    },
    description: {
      control: "text",
    },
    orientation: {
      control: "select",
      options: ["vertical", "horizontal"],
    },
    disabled: {
      control: "boolean",
    },
    required: {
      control: "boolean",
    },
  },
  args: {
    options: Array.from({ length: 10 }, (_, index) => ({
      label: `Option ${index + 1}`,
      value: index + 1,
    })),
    label: "Label test",
    placeholder: "Placeholder test",
    description: "",
    required: false,
    orientation: "vertical",
    disabled: false,
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    name: "defaultField",
    label: "Default",
  },
};

export const NoLabel: Story = {
  args: {
    name: "noLabelField",
    label: "",
  },
};

export const Horizontal: Story = {
  args: {
    name: "horizontalField",
    orientation: "horizontal",
    label: "Horizontal",
  },
};

export const Description: Story = {
  args: {
    name: "descriptionField",
    label: "Description",
    description:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis at nulla vehicula, pulvinar eros eget, sollicitudin justo. Etiam mollis justo vel odio tincidunt imperdiet.",
  },
};

export const Disabled: Story = {
  args: {
    name: "disabled",
    label: "Disabled",
    disabled: true,
  },
};
