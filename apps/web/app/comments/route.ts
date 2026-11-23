import { commentsPage } from "../../server/site/pages.ts";
import { html } from "../../server/site/respond.ts";

export const dynamic = "force-static";

export function GET() {
  return html(commentsPage());
}
