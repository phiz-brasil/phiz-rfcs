import { Shell } from "../../../components/Shell";
import { ThemeDetail } from "../../../components/ThemeDetail";
import { liveConfig } from "../../../server/site/html.ts";

export const metadata = { title: "Tema · PHIZ RFCs" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><ThemeDetail id={id.toUpperCase()} /></Shell>;
}
