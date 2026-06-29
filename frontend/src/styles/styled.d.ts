import "styled-components";

declare module "styled-components" {
  export interface DefaultTheme {
    colors: {
      neutral800: string;
      primary800: string;
      primary700: string;
      primary600: string;
      secondary: string;
      secondary200: string;
      red300: string;
      red20: string;
      skyblue300: string;
      skyblue20: string;
      point: string;
      white: string;
    };
  }
}
