import { PropsWithChildren } from "react";
import { BrowserRouter } from "react-router-dom";
import { render } from "@testing-library/react";
import { AppProviders } from "@/app/providers";

export function renderWithProviders(children: PropsWithChildren["children"]) {
  return render(
    <AppProviders>
      <BrowserRouter>{children}</BrowserRouter>
    </AppProviders>,
  );
}
