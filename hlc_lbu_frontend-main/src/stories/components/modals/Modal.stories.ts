import type { Meta, StoryObj } from "@storybook/vue3-vite";
import Modal from "@/components/modals/base/Modal.vue";
import Button from "@/components/buttons/base/Button.vue";
import ModalGeneric from "@/components/modals/ModalGeneric.vue";
import PageTitle from "@/components/texts/headings/PageTitle.vue";
import ButtonGoBack from "@/components/buttons/ButtonGoBack.vue";
import FieldsContainer from "@/components/forms/base/FieldsContainer.vue";
import FieldText from "@/components/forms/base/FieldText.vue";
import FieldLanguage from "@/components/forms/FieldLanguage.vue";
import FieldTextarea from "@/components/forms/base/FieldTextarea.vue";
import Separator from "@/components/Separator.vue";

const meta: Meta<typeof Modal> = {
  title: "Components/Modals/Modal",
  component: Modal,
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: ["default", "closeButton", "closeOnClickOutside", "maxWidth"],
    },
  },
  argTypes: {
    default: {
      type: "string",
    },
  },
  args: {
    default:
      "Lorem, ipsum dolor sit amet consectetur adipisicing elit. Blanditiis perspiciatis deleniti sequi, sapiente provident nam voluptates id autem quod, porro exercitationem repudiandae quas quae quis officia corrupti, quo dolores omnis.",
    closeButton: true,
    closeOnClickOutside: true,
    maxWidth: 1000,
  },
  render: (args) => ({
    components: { Modal, Button },
    setup() {
      const isOpen = ref(false);

      function close() {
        isOpen.value = false;
      }

      return { args, isOpen, close };
    },
    template: `
      <div>
        <Button @click="isOpen = true">Open</Button>

        <Modal v-model="isOpen" v-bind="args" innerClass="tw:max-w-[1050px] tw:px-10 tw:py-6">
          <p class="tw:whitespace-pre-line">{{ args.default }}</p>
          <Button @click="close">Close</Button>
        </Modal>
      </div>`,
  }),
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Base: Story = {
  args: {},
};

export const BaseWithLongContent: Story = {
  args: {
    default:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin ipsum neque, gravida quis tortor ac, auctor iaculis ante. Praesent odio lectus, pharetra efficitur ultrices et, elementum id orci. Integer varius justo a justo elementum sodales. Praesent posuere risus nec risus placerat, vel semper libero congue. Nullam aliquam orci lectus, iaculis gravida nunc dictum sit amet. Phasellus a scelerisque purus. Integer in lorem condimentum, fringilla purus sed, pretium nibh. Morbi auctor fermentum sem at interdum. Sed convallis, urna sit amet semper porta, dui mi dignissim sem, quis ultricies ligula velit rutrum justo.\n\nPraesent lobortis elit id sagittis gravida. Maecenas in semper odio, sed euismod sapien. Etiam aliquam fermentum sapien vel fringilla. Donec eu augue a metus egestas fringilla vel eu risus. Curabitur porttitor euismod lorem, sed mattis felis sollicitudin sed. Fusce blandit turpis sit amet tortor scelerisque faucibus. Duis magna felis, posuere non nisi mollis, gravida imperdiet est. Integer vitae vehicula velit, non bibendum dolor. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Vestibulum consectetur consequat velit, at aliquet massa.\n\nNam eleifend placerat mi a tristique. In dictum eleifend est non pretium. Sed non ante at risus euismod rutrum non vel justo. Donec laoreet leo ut ipsum varius, vel accumsan arcu mollis. Praesent at ipsum eget enim ultrices egestas. Ut et ante in lectus tempor semper. Pellentesque tincidunt laoreet neque sed consequat. Nulla facilisi. Cras sodales mauris ac urna facilisis aliquet. Proin convallis nibh a accumsan consectetur. Morbi viverra justo non feugiat scelerisque. Pellentesque pretium, velit in blandit mattis, nibh quam elementum lorem, in ultricies quam dolor id ex. Aliquam erat volutpat. Sed id molestie leo. Nunc vitae elit quis mi feugiat vulputate id et dui.\n\nUt tincidunt pellentesque magna in rutrum. Phasellus porttitor eu libero tincidunt interdum. Aenean tincidunt, lacus sit amet consequat convallis, est massa porta sapien, nec suscipit leo dolor et quam. Maecenas placerat laoreet finibus. Fusce facilisis neque nisl, at faucibus massa ullamcorper ac. Vivamus id elit id ipsum venenatis vulputate. Pellentesque et venenatis turpis, eget posuere nisi. Vestibulum eget risus semper, maximus eros at, lobortis tellus.\n\nNam lobortis elementum arcu, id bibendum est pharetra at. Curabitur justo est, congue sodales consectetur in, rhoncus vel lorem. In at suscipit massa. Vivamus sed ullamcorper tellus, id tincidunt neque. Ut pellentesque ligula eget sagittis porttitor. In euismod auctor arcu id maximus. Donec molestie magna lectus, ac tempor nulla tincidunt quis. Nunc eget elit enim. Vivamus tincidunt vel urna eget condimentum. Vestibulum imperdiet, lectus a finibus rutrum, massa lacus tristique eros, ut dapibus nunc dui id nisi. Nullam vehicula nunc at odio laoreet efficitur. Nam commodo enim dolor, vitae interdum ipsum egestas eu. Duis id interdum elit, in malesuada felis. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae;\nLorem ipsum dolor sit amet, consectetur adipiscing elit. Proin ipsum neque, gravida quis tortor ac, auctor iaculis ante. Praesent odio lectus, pharetra efficitur ultrices et, elementum id orci. Integer varius justo a justo elementum sodales. Praesent posuere risus nec risus placerat, vel semper libero congue. Nullam aliquam orci lectus, iaculis gravida nunc dictum sit amet. Phasellus a scelerisque purus. Integer in lorem condimentum, fringilla purus sed, pretium nibh. Morbi auctor fermentum sem at interdum. Sed convallis, urna sit amet semper porta, dui mi dignissim sem, quis ultricies ligula velit rutrum justo.\nPraesent lobortis elit id sagittis gravida. Maecenas in semper odio, sed euismod sapien. Etiam aliquam fermentum sapien vel fringilla. Donec eu augue a metus egestas fringilla vel eu risus. Curabitur porttitor euismod lorem, sed mattis felis sollicitudin sed. Fusce blandit turpis sit amet tortor scelerisque faucibus. Duis magna felis, posuere non nisi mollis, gravida imperdiet est. Integer vitae vehicula velit, non bibendum dolor. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Vestibulum consectetur consequat velit, at aliquet massa.\nNam eleifend placerat mi a tristique. In dictum eleifend est non pretium. Sed non ante at risus euismod rutrum non vel justo. Donec laoreet leo ut ipsum varius, vel accumsan arcu mollis. Praesent at ipsum eget enim ultrices egestas. Ut et ante in lectus tempor semper. Pellentesque tincidunt laoreet neque sed consequat. Nulla facilisi. Cras sodales mauris ac urna facilisis aliquet. Proin convallis nibh a accumsan consectetur. Morbi viverra justo non feugiat scelerisque. Pellentesque pretium, velit in blandit mattis, nibh quam elementum lorem, in ultricies quam dolor id ex. Aliquam erat volutpat. Sed id molestie leo. Nunc vitae elit quis mi feugiat vulputate id et dui.",
  },
};

export const Generic: Story = {
  args: {},
  render: (args) => ({
    components: { ModalGeneric, Button },
    setup() {
      const isOpen = ref(false);

      return { args, isOpen };
    },
    template: `
      <div>
        <Button @click="isOpen = true">Open</Button>

        <ModalGeneric
          v-model="isOpen"
          icon="tabler-calendar"
          name="saveAlert"
          displayShowCheckbox
          @confirm="isOpen = false"
          @cancel="isOpen = false"
        >
          <template #title>
            Lorem ipsum dolor sit amet
          </template>

          <template #description>
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas interdum nisi vitae accumsan tincidunt. Proin pulvinar interdum leo sed pharetra. Etiam molestie nulla libero. Morbi elit nulla, gravida in enim in, scelerisque sollicitudin arcu.
          </template>

          <template #cancel>
            Cancel
          </template>
          <template #continue>
            Confirm
          </template>
        </ModalGeneric>
      </div>`,
  }),
};

export const SaveAlert: Story = {
  args: {},
  render: (args) => ({
    components: { ModalGeneric, Button },
    setup() {
      const isOpen = ref(false);

      return { args, isOpen };
    },
    template: `
      <div>
        <Button @click="isOpen = true">Open</Button>

        <ModalGeneric
          v-model="isOpen"
          icon="tabler:alert-triangle-filled"
          name="saveAlert"
          displayShowCheckbox
          @confirm="isOpen = false"
          @cancel="isOpen = false"
        >
          <template #title>
            {{ $t("savealertmodal.title") }}
          </template>

          <template #description>
            {{ $t("savealertmodal.description") }}
          </template>

          <template #cancel>
            {{ $t("global.stay") }}
          </template>
          <template #continue>
            {{ $t("global.leave") }}
          </template>
        </ModalGeneric>
      </div>`,
  }),
};

export const FormExampleCelennyStyle: Story = {
  args: {},
  render: (args) => ({
    components: {
      Modal,
      PageTitle,
      Button,
      ButtonGoBack,
      FieldsContainer,
      FieldText,
      FieldLanguage,
      FieldTextarea,
    },
    setup() {
      const isOpen = ref(false);

      return { args, isOpen };
    },
    template: `
      <div>
        <Button @click="isOpen = true">Open</Button>

        <Modal
          v-model="isOpen"
          class="tw:px-10 tw:pb-9 tw:pt-8"
          :maxWidth="1036"
          closeButton
        >
          <!-- TODO: add help video URL later -->
          <PageTitle is="h2" class="tw:mb-8">
            Lorem Ipsum

            <template #description>
              Lorem Ipsum
            </template>
          </PageTitle>

          <FieldsContainer class="tw:mb-8">
            <FieldLanguage
              name="language"
              label="Select"
              placeholder="A select field"
            />

            <FieldText
              name="text"
              label="Text"
              placeholder="A text field"
            />

            <FieldTextarea
              name="textarea"
              label="Textarea"
              placeholder="A textarea field"
            />
          </FieldsContainer>

          <div class="tw:flex tw:justify-between">
            <ButtonGoBack class="tw:basis-[260px]" @click="isOpen = false">
              {{ $t("global.back") }}
            </ButtonGoBack>

            <Button class="tw:basis-[260px]" type="button"  @click="isOpen = false">
              {{ $t("global.save") }}
            </Button>
          </div>
        </Modal>
      </div>`,
  }),
};

export const FormExampleFavourStyle: Story = {
  args: {},
  render: (args) => ({
    components: {
      Modal,
      PageTitle,
      Button,
      FieldsContainer,
      FieldText,
      FieldLanguage,
      FieldTextarea,
      Separator,
    },
    setup() {
      const isOpen = ref(false);

      return { args, isOpen };
    },
    template: `
      <div>
        <Button @click="isOpen = true">Open</Button>

        <Modal
          v-model="isOpen"
          :maxWidth="800"
        >
          <h2 class="tw:text-4xl tw:font-extrabold tw:px-10 tw:pt-8 tw:pb-6">
            Lorem Ipsum
          </h2>

          <Separator />

          <FieldsContainer class="tw:px-10 tw:py-6">
            <FieldLanguage
              name="language"
              label="Select"
              placeholder="A select field"
            />

            <FieldText
              name="text"
              label="Text"
              placeholder="A text field"
            />

            <FieldTextarea
              name="textarea"
              label="Textarea"
              placeholder="A textarea field"
            />
          </FieldsContainer>

          <Separator />

          <div class="tw:flex tw:justify-end tw:gap-3 tw:pt-6 tw:pb-10 tw:px-10">
            <Button variant="outlined" @click="isOpen = false">
              Cancel
            </Button>

            <Button @click="isOpen = false">
              Save
            </Button>
          </div>
        </Modal>
      </div>`,
  }),
};
