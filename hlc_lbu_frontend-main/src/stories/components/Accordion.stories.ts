import type { Meta, StoryObj } from "@storybook/vue3-vite";
import Accordion from "@/components/accordions/Accordion.vue";
import { iconCardVariants } from "@/components/cards/IconCard.vue";

const meta: Meta<typeof Accordion> = {
  title: "Components/Accordions/Accordion",
  component: Accordion,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: ["title", "default", "variant", "icon", "iconVariant"],
    },
  },
  argTypes: {
    title: {
      control: "text",
    },
    default: {
      control: "text",
    },
    variant: {
      control: "select",
      options: ["default", "solid"],
    },
    icon: {
      control: "text",
      description: "Iconify code. Example: **tabler-calendar**",
    },
    iconVariant: {
      control: "select",
      options: iconCardVariants,
    },
  },
  args: {
    title: "Title",
    default:
      "Lorem, ipsum dolor sit amet consectetur adipisicing elit. Blanditiis perspiciatis deleniti sequi, sapiente provident nam voluptates id autem quod, porro exercitationem repudiandae quas quae quis officia corrupti, quo dolores omnis.",
    variant: "default",
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {},
};

export const Solid: Story = {
  args: {
    variant: "solid",
  },
};

export const WithIcon: Story = {
  args: {
    title: "With Icon",
    icon: "tabler-calendar",
  },
};

export const WithIconVariant: Story = {
  args: {
    title: "With Icon",
    icon: "tabler-calendar",
    iconVariant: "primary",
  },
};

export const CheckboxNotification: Story = {
  args: {
    title: "With Icon",
    icon: "tabler-calendar",
    iconVariant: "primary",
  },
  render: (args) => ({
    components: { Accordion },
    setup() {
      console.log(args);
      return { args };
    },
    template: `
      <Accordion v-bind="args">
        <template #title>
          Lorem Ipsum
        </template>

        Lorem Ipsum
      </Accordion>`,
  }),
};
