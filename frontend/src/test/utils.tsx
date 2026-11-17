import type { ReactElement, ReactNode } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
}

interface RenderOptions {
  route?: string;
  /** Route path pattern used to mount `ui` — set to "/flyers/:id" for param pages. Defaults to "*". */
  routePath?: string;
  /** Extra routes for navigation assertions, e.g. [["/", <div>HOME</div>]]. */
  routes?: Array<[string, ReactNode]>;
}

export function renderWithProviders(ui: ReactElement, { route = "/", routePath, routes = [] }: RenderOptions = {}) {
  const client = makeQueryClient();
  const tree = (
    <Routes>
      <Route path={routePath ?? "*"} element={ui} />
      {routes.map(([path, element]) => (
        <Route key={path} path={path} element={<>{element}</>} />
      ))}
    </Routes>
  );
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>{tree}</MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}
