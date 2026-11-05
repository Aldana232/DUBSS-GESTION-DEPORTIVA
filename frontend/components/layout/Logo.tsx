import Image from "next/image";
import { cn } from "@/lib/utils";

/** Escudo institucional de la DUBSS (public/logo-dubss.png). */
export function Logo({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <Image
      src="/logo-dubss.png"
      alt="Escudo de la Dirección Universitaria de Bienestar Social y Salud (DUBSS)"
      width={size}
      height={size}
      priority
      className={cn("rounded-full bg-white", className)}
    />
  );
}
