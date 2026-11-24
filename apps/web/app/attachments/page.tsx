import { Shell } from "../../components/Shell";
import { AttachmentsPage } from "../../components/AttachmentsPage";
import { liveConfig } from "../../server/site/html.ts";

export const metadata = { title: "Anexos · PhizChat Command Center" };

export default function Page() {
  const c = liveConfig().comments as { supabaseUrl: string; supabaseKey: string };
  return <Shell supabase={{ url: c.supabaseUrl, key: c.supabaseKey }}><AttachmentsPage /></Shell>;
}
