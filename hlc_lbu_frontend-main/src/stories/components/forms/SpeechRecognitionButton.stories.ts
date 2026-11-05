import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SpeechRecognitionButton from "@/components/forms/base/speech-recognition/SpeechRecognitionButton.vue";

const meta: Meta<typeof SpeechRecognitionButton> = {
  title: "Components/Forms/SpeechRecognitionButton",
  component: SpeechRecognitionButton,
  tags: ["autodocs"],
  parameters: {
    controls: {},
  },
  argTypes: {},
  args: {},
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {},
};
