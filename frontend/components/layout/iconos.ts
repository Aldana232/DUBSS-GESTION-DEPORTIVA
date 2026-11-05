import {
  Bell, BrainCircuit, Mic, Smartphone, CalendarDays, CalendarRange, ClipboardCheck, FileBarChart, LayoutDashboard, MessageSquareWarning,
  ScrollText, Settings2, Shield, Trophy, Users, type LucideIcon,
} from "lucide-react";
import type { IconoMenu } from "@/lib/auth/roles";

export const ICONOS: Record<IconoMenu, LucideIcon> = {
  inicio: LayoutDashboard,
  campeonatos: Trophy,
  inscripciones: ClipboardCheck,
  fixture: CalendarDays,
  predicciones: BrainCircuit,
  quejas: MessageSquareWarning,
  reportes: FileBarChart,
  catalogos: Settings2,
  usuarios: Users,
  bitacora: ScrollText,
  equipos: Shield,
  calendario: CalendarRange,
  asistente: Mic,
  notificaciones: Bell,
  planilla: Smartphone,
};

