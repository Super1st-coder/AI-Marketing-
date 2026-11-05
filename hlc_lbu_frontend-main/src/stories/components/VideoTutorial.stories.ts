import type { Meta, StoryObj } from "@storybook/vue3-vite";
import VideoTutorial from "@/components/videos/VideoTutorial.vue";

const meta: Meta<typeof VideoTutorial> = {
  title: "Components/VideoTutorial",
  component: VideoTutorial,
  tags: ["autodocs"],
  parameters: {
    docs: {
      controls: {
        include: ["chip", "title", "description"],
      },
    },
  },
  argTypes: {
    chip: {
      type: "string",
    },
    title: {
      type: "string",
    },
    description: {
      type: "string",
    },
  },
  args: {},
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    chip: "Chip Text",
    title: "Large Title",
    description:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras eleifend ullamcorper nunc, eu gravida risus facilisis ut. Vivamus eu turpis id massa egestas tincidunt sit amet nec lectus. Aliquam sem ligula, varius ac rhoncus auctor, vulputate eu nisi. Aliquam tincidunt est orci. Vivamus efficitur sed dui quis lobortis. Curabitur imperdiet magna in metus egestas lacinia. Nulla facilisi. Nullam blandit enim nibh, et volutpat lectus aliquet eget.",
  },
};
