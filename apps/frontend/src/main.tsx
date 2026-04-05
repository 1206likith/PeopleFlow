import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "@/app/App";
import "@/styles/base.css";
import "@/styles/theme.css";
import "@/styles/variables.css";
import "@/styles/themes.css";
import "@/styles/research-dashboard.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
