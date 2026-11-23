import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

const roots = ["react-login", "react-landing"]
  .map((id) => document.getElementById(id))
  .filter(Boolean);

for (const root of roots) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
