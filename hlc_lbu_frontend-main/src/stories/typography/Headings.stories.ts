import type { Meta, StoryObj } from "@storybook/vue3-vite";

const meta: Meta = {
  title: "Typography/Headings",
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj;

export const Headings: Story = {
  render: () => ({
    template: `
      <div class="space-y-4">
        <h1 class="tw:text-4xl tw:font-bold">Heading 1</h1>
        <h2 class="tw:text-3xl tw:font-semibold">Heading 2</h2>
        <h3 class="tw:text-2xl tw:font-medium">Heading 3</h3>
        <h4 class="tw:text-xl tw:font-medium">Heading 4</h4>
        <h5 class="tw:text-lg tw:font-normal">Heading 5</h5>
        <h6 class="tw:text-base tw:font-normal">Heading 6</h6>
      </div>
    `,
  }),
};
