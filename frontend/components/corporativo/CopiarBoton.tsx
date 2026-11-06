"use client";
import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui";

/** Copia un texto al portapapeles; si el navegador lo impide, avisa para copiarlo a mano. */
export function CopiarBoton({ texto, etiqueta = "Copiar" }: { texto: string; etiqueta?: string }) {
  const [estado, setEstado] = useState<"idle" | "ok" | "error">("idle");
  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setEstado("ok");
    } catch {
      setEstado("error");
    }
    setTimeout(() => setEstado("idle"), 1800);
  }
  return (
    <Button variant="secondary" size="sm" onClick={copiar} icon={estado === "ok" ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}>
      {estado === "ok" ? "Copiado" : estado === "error" ? "Cópialo a mano" : etiqueta}
    </Button>
  );
}
