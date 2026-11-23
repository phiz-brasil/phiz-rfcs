import { Shell } from "../../components/Shell";
import { RoadmapPage } from "../../components/RoadmapPage";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "Roadmap · PHIZ RFCs" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><RoadmapPage /></Shell>;
}
