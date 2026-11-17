"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Button, Checkbox, Modal } from "@/components/ui";
import { guardarConsentimiento, leerConsentimiento } from "@/lib/consentimiento";

/** Panel de preferencias de cookies: se abre desde el aviso («Configurar») o desde el pie de cualquier página. */
export function PanelCookies({ abierto, onCerrar }: { abierto: boolean; onCerrar: () => void }) {
  const [preferencias, setPreferencias] = useState(false);

  useEffect(() => { if (abierto) setPreferencias(leerConsentimiento()?.preferencias ?? false); }, [abierto]);
  const elegir = (valor: boolean) => { guardarConsentimiento(valor); onCerrar(); };

  return (
    <Modal open={abierto} onClose={onCerrar} title="Preferencias de cookies" size="md"
      footer={(
        <div className="flex w-full flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={() => elegir(false)}>Rechazar opcionales</Button>
          <Button variant="secondary" onClick={() => elegir(true)}>Aceptar todas</Button>
          <Button onClick={() => elegir(preferencias)}>Guardar mi elección</Button>
        </div>
      )}>
      <div className="space-y-4 text-sm text-ink-700">
        <p>Elige qué podemos guardar en tu dispositivo. Puedes cambiarlo cuando quieras desde «Configurar cookies», en el pie de cualquier página. Más detalle en la <Link href="/cookies" onClick={onCerrar} className="font-medium text-brand-700 underline">Política de cookies</Link>.</p>

        <div className="rounded-lg border border-ink-200 p-3">
          <Checkbox label="Necesarias" checked disabled readOnly onChange={() => undefined} />
          <p className="mt-1 pl-7 text-xs text-ink-600">Mantienen tu sesión, recuerdan esta elección y permiten usar la planilla sin conexión. Siempre activas: sin ellas el sistema no funciona.</p>
        </div>
        <div className="rounded-lg border border-ink-200 p-3">
          <Checkbox label="Preferencias" checked={preferencias} onChange={(e) => setPreferencias(e.target.checked)} />
          <p className="mt-1 pl-7 text-xs text-ink-600">Recuerdan cómo prefieres ver el sistema (por ejemplo, el menú lateral contraído). Si las desactivas, todo funciona igual.</p>
        </div>
        <div className="rounded-lg border border-dashed border-ink-200 bg-ink-50 p-3">
          <p className="font-medium text-ink-900">Analítica y publicidad</p>
          <p className="mt-1 text-xs text-ink-600">No utilizamos ninguna. No hay nada que activar.</p>
        </div>
      </div>
    </Modal>
  );
}
