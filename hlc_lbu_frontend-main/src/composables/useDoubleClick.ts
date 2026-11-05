export default function useDoubleClick(
  firstClick: () => Promise<void> | void,
  secondClick: () => Promise<void> | void,
) {
  const hasBeenClicked = ref(false);

  const action = async () => {
    if (hasBeenClicked.value) {
      await secondClick();
      hasBeenClicked.value = false;
    } else {
      hasBeenClicked.value = true;
      await firstClick?.();
    }
  };

  return {
    action,
    hasBeenClicked,
  };
}
