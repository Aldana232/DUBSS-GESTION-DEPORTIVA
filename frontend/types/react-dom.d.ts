// El proyecto no instala @types/react-dom; solo se usa createPortal (cajones fuera del encabezado).
declare module "react-dom" {
  import type { ReactNode, ReactPortal } from "react";
  export function createPortal(children: ReactNode, container: Element | DocumentFragment, key?: string | null): ReactPortal;
}
