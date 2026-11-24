import { Shell } from "../../components/Shell";
import { SlidesPage } from "../../components/SlidesPage";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "Slides · PhizChat Command Center" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><SlidesPage /></Shell>;
}
