import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** Salud del frontend (Docker y monitores). No toca la API ni la sesión. */
export function GET() {
  return NextResponse.json({ estado: "ok" });
}
