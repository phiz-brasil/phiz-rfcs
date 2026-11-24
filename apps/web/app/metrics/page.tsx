import { Shell } from "../../components/Shell";
import { MetricsPage } from "../../components/MetricsPage";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "Métricas · PhizChat Command Center" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><MetricsPage /></Shell>;
}
