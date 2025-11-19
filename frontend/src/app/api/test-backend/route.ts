export async function GET() {
  const url = process.env.NEXT_PUBLIC_BACKEND_URL!;
  try {
    const r = await fetch(url, { cache: "no-store" });
    return Response.json({ ok: r.ok, status: r.status });
  } catch (e: any) {
    return Response.json({ error: String(e), url });
  }
}
