import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { registerSW } from "virtual:pwa-register";
import { App } from "./App";
import { SettingsProvider } from "./settings";
import { SpeechProvider } from "./speech";
import "./styles.css";

registerSW({ immediate: true });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <SettingsProvider>
        <SpeechProvider>
          <App />
        </SpeechProvider>
      </SettingsProvider>
    </BrowserRouter>
  </StrictMode>,
);
