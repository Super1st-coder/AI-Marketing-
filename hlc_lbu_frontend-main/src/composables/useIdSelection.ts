export function useIdSelection(selectedIds: Ref<number[]>) {
  const toggle = (id: number) => {
    const index = selectedIds.value.indexOf(id);
    if (index > -1) {
      selectedIds.value.splice(index, 1);
    } else {
      selectedIds.value.push(id);
    }
  };

  const isSelected = (id: number) => selectedIds.value.includes(id);

  const clear = () => {
    selectedIds.value = [];
  };

  return { toggle, isSelected, clear };
}
