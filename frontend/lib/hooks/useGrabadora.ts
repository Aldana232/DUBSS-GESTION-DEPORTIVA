"use client";
import { useEffect, useRef, useState } from "react";
import { useToast } from "@/components/ui/Toast";
import { useAccion } from "@/lib/hooks/queries";
import { asistenteService } from "@/lib/api/services";

/** Graba audio del micrófono y lo transcribe en el servidor (Whisper). El texto se entrega a `alTranscribir`. */
export function useGrabadora(alTranscribir: (texto: string) => void) {
  const toast = useToast();
  const [grabando, setGrabando] = useState(false);
  const grabadora = useRef<MediaRecorder | null>(null);
  const partes = useRef<Blob[]>([]);
  const transcribir = useAccion((audio: Blob) => asistenteService.transcribir(audio), { error: "No se pudo transcribir el audio." });

  useEffect(() => () => { grabadora.current?.stream.getTracks().forEach((t) => t.stop()); }, []);

  const iniciar = async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      toast.error("Este navegador no permite grabar audio. Escribe el mensaje.");
      return;
    }
    try {
      const flujo = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(flujo);
      partes.current = [];
      mr.ondataavailable = (e) => { if (e.data.size) partes.current.push(e.data); };
      mr.onstop = () => {
        flujo.getTracks().forEach((t) => t.stop());
        transcribir.ejecutar(new Blob(partes.current, { type: mr.mimeType || "audio/webm" }), { onSuccess: (r) => alTranscribir(r.texto) });
      };
      mr.start();
      grabadora.current = mr;
      setGrabando(true);
    } catch {
      toast.error("No se pudo acceder al micrófono. Revisa los permisos o escribe el mensaje.");
    }
  };
  const detener = () => { grabadora.current?.stop(); setGrabando(false); };

  return { grabando, transcribiendo: transcribir.pendiente, iniciar, detener };
}
