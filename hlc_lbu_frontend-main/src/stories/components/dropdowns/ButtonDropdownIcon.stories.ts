import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ButtonDropdownIcon from "@/components/buttons/base/ButtonDropdownIcon.vue";
import ButtonDropdownOption from "@/components/buttons/base/ButtonDropdownOption.vue";

const meta: Meta<typeof ButtonDropdownIcon> = {
  title: "Components/Dropdowns/ButtonDropdownIcon",
  component: ButtonDropdownIcon,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: ["icon", "placement"],
    },
  },
  argTypes: {
    icon: {
      control: "text",
      description: "Iconify code. Example: **tabler-calendar**",
    },
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
    icon: "tabler-dots",
    placement: "bottom",
  },
  render: (args) => ({
    components: { ButtonDropdownIcon, ButtonDropdownOption },
    setup() {
      return { args };
    },
    template: `
      <ButtonDropdownIcon v-bind="args">
        {{ args.default }}
        <template #options>
          <ButtonDropdownOption>Simple option</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-calendar">Option with icon</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-calendar" color="primary">Option 3</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-check" color="success">Option 4</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-check" color="success" disabled>Disabled option</ButtonDropdownOption>
          <ButtonDropdownOption icon="tabler-check" color="success" disabled>Disabled option</ButtonDropdownOption>
        </template>
      </ButtonDropdownIcon>`,
  }),
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {},
};
