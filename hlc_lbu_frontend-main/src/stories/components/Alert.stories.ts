import type { Meta, StoryObj } from "@storybook/vue3-vite";
import Alert from "@/components/alerts/Alert.vue";

const meta: Meta<typeof Alert> = {
  title: "Components/Alert",
  component: Alert,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: ["default", "type"],
    },
  },
  argTypes: {
    default: {
      control: "text",
    },
    type: {
      control: "select",
      options: ["secondary", "error", "warning", "success"],
    },
  },
  args: {
    default:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis commodo interdum orci sit amet aliquam. Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    type: "error",
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Error: Story = {
  args: {},
};
