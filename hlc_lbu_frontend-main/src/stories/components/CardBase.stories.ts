import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CardBase from "@/components/cards/base/CardBase.vue";

const meta: Meta<typeof CardBase> = {
  title: "Components/CardBase",
  component: CardBase,
  tags: ["autodocs"],
  parameters: {
    docs: {
      controls: {
        include: ["color", "hoverColor", "outlineColor"],
      },
    },
  },
  argTypes: {
    color: {
      control: "select",
      options: ["default", "primary"],
    },
    hoverColor: {
      control: "select",
      options: ["default", "primary"],
    },
    outlineColor: {
      control: "select",
      options: ["default", "primary", "success", "error"],
    },
  },

  args: {
    color: "default",
    hoverColor: undefined,
    outlineColor: "default",
    default:
      "<div class='tw:p-5'><h1>Test</h1><p>Lorem ipsum dolor sit amet</p></p>",
  },
  render: (args) => ({
    components: { CardBase },
    setup() {
      return { args };
    },
    template: `
      <CardBase v-bind="args">
        <div v-html="args.default"></div>
      </CardBase>
    `,
  }),
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    color: "default",
  },
};

export const Primary: Story = {
  args: {
    color: "primary",
  },
};

export const WithOutline: Story = {
  args: {
    outlineColor: "primary",
  },
};
