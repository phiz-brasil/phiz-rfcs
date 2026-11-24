import { Shell } from "../../components/Shell";
import { BoardPage } from "../../components/BoardPage";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "Quadro B2B · PhizChat Command Center" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><BoardPage /></Shell>;
}
