import type { Meta, StoryObj } from "@storybook/vue3-vite";

const meta: Meta = {
  title: "Colors/Text",
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => ({
    template: `
        <p class="tw:text-primary-text">
          Primary Text
        </p>

        <p class="tw:text-secondary-text">
          Secondary Text
        </p>

        <p class="tw:text-primary">
          Primary
        </p>

        <p class="tw:text-secondary">
          Secondary
        </p>

        <p class="tw:text-info">
          Info
        </p>

        <p class="tw:text-info-light">
          Info Light
        </p>

        <p class="tw:text-success">
          Success
        </p>

        <p class="tw:text-success-light">
          Success Light
        </p>

        <p class="tw:text-warning">
          Warning
        </p>

         <p class="tw:text-warning-light">
          Warning Light
        </p>

        <p class="tw:text-error">
          Error
        </p>

        <p class="tw:text-error-light">
          Error Light
        </p>
    `,
  }),
};
