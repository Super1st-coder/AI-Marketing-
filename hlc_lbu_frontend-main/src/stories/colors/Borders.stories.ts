import type { Meta, StoryObj } from "@storybook/vue3-vite";

const meta: Meta = {
  title: "Colors/Borders",
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => ({
    template: `
      <div class="tw:container tw:py-4">
        <div class="tw:grid tw:grid-cols-10 tw:gap-1 tw:mb-4">
          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-primary">
            Primary
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-secondary">
            Secondary
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-info">
            Info
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-info-light">
            Info Light
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-success">
            Success
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-success-light">
            Success Light
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-warning">
            Warning
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-warning-light">
            Light
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-error">
            Error
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-error-light">
            Error Light
          </div>
        </div>

        <Separator />

        <div class="tw:grid tw:grid-cols-10 tw:gap-1 tw:mb-4 tw:font-medium">
          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-divider">
            Divider
          </div>

          <div class="tw:flex tw:justify-center tw:items-center tw:text-center tw:aspect-square tw:border-2 tw:border-input-border">
            Input Border
          </div>
        </div>
      </div>
    `,
  }),
};
