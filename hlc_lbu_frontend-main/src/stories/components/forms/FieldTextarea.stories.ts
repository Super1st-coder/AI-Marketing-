import type { Meta, StoryObj } from "@storybook/vue3-vite";
import FieldTextarea from "@/components/forms/base/FieldTextarea.vue";

const meta: Meta<typeof FieldTextarea> = {
  title: "Components/Forms/FieldTextarea",
  component: FieldTextarea,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: [
        "label",
        "placeholder",
        "description",
        "orientation",
        "disabled",
        "required",
        "speechRecognition",
      ],
    },
  },
  argTypes: {
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
    speechRecognition: {
      control: "boolean",
    },
  },
  args: {
    label: "Label test",
    placeholder: "Placeholder test",
    description: "",
    required: false,
    orientation: "vertical",
    disabled: false,
    speechRecognition: false,
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    name: "default",
    label: "Default",
  },
};

export const NoLabel: Story = {
  args: {
    name: "default",
    label: "",
  },
};

export const Horizontal: Story = {
  args: {
    name: "horizontal",
    orientation: "horizontal",
    label: "Horizontal",
  },
};

export const Description: Story = {
  args: {
    name: "description",
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

export const SpeechRecognition: Story = {
  args: {
    name: "speechRecognition",
    speechRecognition: true,
  },
};
