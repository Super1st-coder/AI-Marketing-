import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CardDashboardGridLocal from "@/components/cards/CardDashboardGridLocal.vue";
import Button from "@/components/buttons/base/Button.vue";
import CardBase from "@/components/cards/base/CardBase.vue";

type Item = {
  id: number;
  name: string;
};

const items = [...Array(100)].map<Item>((_, index) => ({
  id: index,
  name: `Item ${index + 1}`,
}));

const meta: Meta<typeof CardDashboardGridLocal> = {
  title: "Components/CardDashboardGridLocal",
  tags: ["autodocs"],
  parameters: {
    docs: {
      controls: {
        include: ["searchPlaceholder", "pageSize"],
      },
    },
  },
  argTypes: {},
  args: {
    searchPlaceholder: "Search text",
    pageSize: 9,
  },
  render: (args) => ({
    components: { CardDashboardGridLocal, Button, CardBase },
    setup() {
      const { t } = useI18n();

      const sorters = [
        {
          name: "name",
          label: t("sorter.name"),
          sort: (a, b) =>
            a.name.localeCompare(b.name, undefined, { numeric: true }),
        },
      ];

      return { args, sorters, items };
    },
    template: `
      <CardDashboardGridLocal
        itemsIdKey="id"
        :items="items"
        spacing="md"
        :sorters="sorters"
        defaultSorter="name"
        v-bind="args"
      >
        <template #item="item">
          <CardBase class="tw:flex tw:flex-col tw:gap-5 tw:p-6">
            {{item.name}}
          </CardBase>
        </template>

        <template #actions>
          <Button leftIcon="tabler-plus" :to="{ name: 'CreateBrand' }">
            Action
          </Button>
        </template>
      </CardDashboardGridLocal>`,
  }),
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {},
};
