import { PublicShell } from "@/components/layout/PublicShell";

export default function PublicoLayout({ children }: { children: React.ReactNode }) {
  return <PublicShell>{children}</PublicShell>;
}
