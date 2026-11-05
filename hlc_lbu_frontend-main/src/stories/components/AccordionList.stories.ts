import type { Meta, StoryObj } from "@storybook/vue3-vite";
import Accordion from "@/components/accordions/Accordion.vue";
import AccordionList from "@/components/accordions/AccordionList.vue";

const meta: Meta<typeof AccordionList> = {
  title: "Components/Accordions/AccordionList",
  component: AccordionList,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: ["variant"],
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "solid"],
    },
  },
  args: {
    variant: "default",
  },
  render: (args) => ({
    components: { AccordionList, Accordion },
    setup() {
      return { args };
    },
    template: `
      <AccordionList v-bind="args">
        <Accordion>
          <template #title>
            Lorem Ipsum 1
          </template>

          <p class="tw:mb-2">Lorem, ipsum dolor sit amet consectetur adipisicing elit. Blanditiis perspiciatis deleniti sequi, sapiente provident nam voluptates id autem quod, porro exercitationem repudiandae quas quae quis officia corrupti, quo dolores omnis.</p>
          <p>Lorem, ipsum dolor sit amet consectetur adipisicing elit. Blanditiis perspiciatis deleniti sequi, sapiente provident nam voluptates id autem quod, porro exercitationem repudiandae quas quae quis officia corrupti, quo dolores omnis.</p>
        </Accordion>

        <Accordion>
          <template #title>
            Lorem Ipsum 2
          </template>

          Lorem, ipsum dolor sit amet consectetur adipisicing elit. Blanditiis perspiciatis deleniti sequi, sapiente provident nam voluptates id autem quod, porro exercitationem repudiandae quas quae quis officia corrupti, quo dolores omnis.
        </Accordion>
      </AccordionList>`,
  }),
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
