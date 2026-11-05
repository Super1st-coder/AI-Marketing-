import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PageTitle from "@/components/texts/headings/PageTitle.vue";

const meta: Meta<typeof PageTitle> = {
  title: "Components/PageTitle",
  component: PageTitle,
  tags: ["autodocs"],
  parameters: {
    docs: {
      controls: {
        include: ["default", "description", "helpButton", "youtubeUrl"],
      },
    },
  },
  argTypes: {
    default: {
      type: "string",
    },
    description: { type: "string" },
  },
  args: {
    default: "Lorem Ipsum",
    helpButton: true,
    helpVideoUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    description: "",
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {},
};

export const WithDescription: Story = {
  args: {
    description:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin ipsum neque, gravida quis tortor ac, auctor iaculis ante. Praesent odio lectus, pharetra efficitur ultrices et, elementum id orci.",
  },
};
