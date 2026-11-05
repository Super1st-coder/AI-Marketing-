export type FieldBasicProps = {
  name?: string;
  label?: string;
  required?: boolean;
  /** Shows an "Optional" hint aligned to the right of the label. */
  optional?: boolean;
  description?: string;
  error?: string;
  disabled?: boolean;
  loading?: boolean;
};

export type FieldLayoutProps = {
  orientation?: "horizontal" | "vertical";
  hideLayout?: boolean;
  labelClass?: ClassName;
};

export type FieldInputBasicProps = FieldBasicProps &
  FieldLayoutProps & {
    placeholder?: string;
    leftIcon?: string;
    rightIcon?: string;
    leftIconClass?: ClassName;
    rightIconClass?: ClassName;
    leftIconClickable?: boolean;
    rightIconClickable?: boolean;
    inputClass?: ClassName;
  };

export type FieldInputTextBasicProps = FieldInputBasicProps & {
  speechRecognition?: boolean;
};

export type FileFormat<T extends string> = {
  name: T;
  type: string[];
  icon?: string;
  imagePreview?: boolean;
  /** Plays the video in the thumbnail. */
  videoPreview?: boolean;
};
