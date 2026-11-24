import { ExecutivePage } from "../../components/ExecutivePage";
import { Shell } from "../../components/Shell";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "Visão executiva · PhizChat Command Center" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><ExecutivePage /></Shell>;
}
