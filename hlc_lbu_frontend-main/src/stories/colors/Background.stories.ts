import type { Meta, StoryObj } from "@storybook/vue3-vite";

const meta: Meta = {
  title: "Colors/Background",
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => ({
    template: `
      <div class="tw:container tw:py-4">
        <div class="tw:grid tw:grid-cols-10 tw:gap-1 tw:mb-4 tw:font-medium">
          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:text-white tw:bg-primary">
            Primary
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:text-white tw:bg-secondary">
            Secondary
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:text-white tw:bg-info">
            Info
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:bg-info-light">
            Info Light
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:text-white tw:bg-success">
            Success
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:bg-success-light">
            Success Light
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:text-white tw:bg-warning">
            Warning
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:bg-warning-light">
            Light
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:text-white tw:bg-error">
            Error
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:bg-error-light">
            Error Light
          </div>
        </div>
      </div>
    `,
  }),
};
