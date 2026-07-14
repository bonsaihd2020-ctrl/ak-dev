import React from "react";
import ReactDOM from "react-dom/client";
import { ChakraProvider, ColorModeScript, extendTheme } from "@chakra-ui/react";
import App from "./App";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";

const theme = extendTheme({
  config: { initialColorMode: "dark", useSystemColorMode: false },
  colors: {
    brand: {
      50: "#e6f7ff",
      100: "#b3e0ff",
      200: "#80c9ff",
      300: "#4db2ff",
      400: "#1a9bff",
      500: "#0070e0",
      600: "#005bb3",
      700: "#004786",
      800: "#003359",
      900: "#001f2d",
    },
    dark: {
      bg: "#0a0a0f",
      card: "#12121a",
      border: "#1e1e2e",
      hover: "#1a1a28",
    },
  },
  fonts: { heading: "Inter", body: "Inter" },
  styles: {
    global: {
      body: { bg: "#0a0a0f", color: "white" },
      "*::-webkit-scrollbar": { width: "6px" },
      "*::-webkit-scrollbar-track": { bg: "transparent" },
      "*::-webkit-scrollbar-thumb": { bg: "#333", borderRadius: "3px" },
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ColorModeScript initialColorMode={theme.config.initialColorMode} />
    <ChakraProvider theme={theme}>
      <App />
    </ChakraProvider>
  </React.StrictMode>
);
