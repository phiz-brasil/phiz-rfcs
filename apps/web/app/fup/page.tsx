import { FupList } from "../../components/FupList";
import { Shell } from "../../components/Shell";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "FUP · PhizChat Command Center" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><FupList /></Shell>;
}
