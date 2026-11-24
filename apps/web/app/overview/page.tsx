import { Shell } from "../../components/Shell";
import { OverviewPage } from "../../components/OverviewPage";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "Visão geral · PhizChat Command Center" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><OverviewPage /></Shell>;
}
