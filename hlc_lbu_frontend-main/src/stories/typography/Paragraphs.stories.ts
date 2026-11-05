import type { Meta, StoryObj } from "@storybook/vue3-vite";

const meta: Meta = {
  title: "Typography/Paragraphs",
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component:
          "Ejemplos de párrafos con diferentes tamaños de texto usando TailwindCSS.",
      },
    },
  },
};

export default meta;
type Story = StoryObj;

export const Paragraphs: Story = {
  render: () => ({
    template: `
      <div class="space-y-4">
       <p class="tw:text-xs">
          Texto extra pequeño (tw:text-xs)
        </p>

        <p class="tw:text-sm">
          Texto pequeño (tw:text-sm) — ideal para notas o disclaimers.
        </p>

        <p class="tw:text-base">
          Texto base (tw:text-base) — tamaño estándar de párrafo.
        </p>

        <p class="tw:text-lg">
          Texto grande (tw:text-lg) — útil para resaltar contenido principal.
        </p>

        <p class="tw:text-xl">
          Texto extra grande (tw:text-xl) — se usa en descripciones destacadas.
        </p>

        <p class="tw:text-2xl">
          Texto 2XL (tw:text-2xl) — más prominente, puede servir para subtítulos largos.
        </p>

        <p class="tw:text-3xl">
          Texto 3XL (tw:text-3xl)
        </p>

        <p class="tw:text-4xl">
          Texto 4XL (tw:text-4xl)
        </p>

        <p class="tw:text-5xl">
          Texto 5XL (tw:text-5xl)
        </p>
      </div>
    `,
  }),
};
