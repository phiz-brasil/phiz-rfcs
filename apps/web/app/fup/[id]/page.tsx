import { FupMeeting } from "../../../components/FupMeeting";
import { Shell } from "../../../components/Shell";
import { liveConfig } from "../../../server/site/html.ts";

export const metadata = { title: "FUP · PhizChat Command Center" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><FupMeeting id={id.toLowerCase()} /></Shell>;
}
