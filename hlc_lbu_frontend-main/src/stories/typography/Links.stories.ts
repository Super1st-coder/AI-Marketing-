import type { Meta, StoryObj } from "@storybook/vue3-vite";

const meta: Meta = {
  title: "Typography/Links",
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Ejemplos de enlaces (links) con clases de TailwindCSS.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Links: Story = {
  render: () => ({
    template: `
      <div class="tw:space-y-4">
        <a href="#" class="tw:text-primary tw:hover:text-primary tw:underline">
          Link básico
        </a>
      </div>
    `,
  }),
};
