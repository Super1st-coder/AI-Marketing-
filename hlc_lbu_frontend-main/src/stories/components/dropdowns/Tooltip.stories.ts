import type { Meta, StoryObj } from "@storybook/vue3-vite";
import Tooltip from "@/components/dropdowns/base/Tooltip.vue";
import Button from "@/components/buttons/base/Button.vue";

const meta: Meta<typeof Tooltip> = {
  title: "Components/Dropdowns/Tooltip",
  component: Tooltip,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: ["placement"],
    },
  },
  argTypes: {
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
  },
  args: {
    placement: "bottom",
  },
  render: (args) => ({
    components: { Tooltip, Button },
    setup() {
      return { args };
    },
    template: `
      <Tooltip>
        <Button icon="custom:hi-luca">
          Hover me
        </Button>

        <template #content>
          {{ $t("funnel-flow.paid-social.ads.refine.editor.generate-text-tooltip") }}
        </template>
      </Tooltip>`,
  }),
};

export default meta;
type Story = StoryObj<typeof meta>;

export const OnButton: Story = {
  args: {},
};

export const OnText: Story = {
  args: {},
  render: (args) => ({
    components: { Tooltip, Button },
    setup() {
      return { args };
    },
    template: `
      <Tooltip>
        <p>Hover me!</p>

        <template #content>
          {{ $t("funnel-flow.paid-social.ads.refine.editor.generate-text-tooltip") }}
        </template>
      </Tooltip>`,
  }),
};

export const OnDiv: Story = {
  args: {},
  render: (args) => ({
    components: { Tooltip, Button },
    setup() {
      return { args };
    },
    template: `
      <Tooltip>
        <div class="tw:bg-info tw:aspect-square tw:flex tw:justify-center tw:items-center tw:p-2 tw:text-white">Hover me!</div>

        <template #content>
          {{ $t("funnel-flow.paid-social.ads.refine.editor.generate-text-tooltip") }}
        </template>
      </Tooltip>`,
  }),
};
