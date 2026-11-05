function useDoubleClickWithMessage(
  onSecondClick: () => Promise<void> | void,
  messageRef: Ref<string | undefined>,
  message: MaybeRefOrGetter<string>,
) {
  const firstClick = async () => {
    messageRef.value = toValue(message);
  };

  const secondClick = async () => {
    await onSecondClick();
    messageRef.value = undefined;
  };

  const { action, hasBeenClicked } = useDoubleClick(firstClick, secondClick);

  // Reset state if the message is erased outside of the composable
  watch(messageRef, (message) => {
    if (!message) {
      hasBeenClicked.value = false;
    }
  });

  return action;
}

export default useDoubleClickWithMessage;
