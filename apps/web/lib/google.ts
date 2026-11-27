/* "Criar no Google Slides" (docs/spec/v2/redesign.md, What PR 3 delivers): the person signs in with Google Identity Services, only for the scope
   drive.file (the app sees only the files it creates); the .pptx is uploaded to their Drive with conversion to Google Slides. The token stays in this
   module, in the memory of the tab: never stored, never sent anywhere but Google. */
const GIS = "https://accounts.google.com/gsi/client";
const SCOPE = "https://www.googleapis.com/auth/drive.file";
const UPLOAD = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id";

type TokenAnswer = { access_token?: string; error?: string };
type Gis = { accounts: { oauth2: { initTokenClient: (c: { client_id: string; scope: string; callback: (r: TokenAnswer) => void; error_callback?: (e: unknown) => void }) => { requestAccessToken: () => void } } } };

let token: { value: string; until: number } | null = null;
let loading: Promise<void> | null = null;

/* The client id: the one of site.config.json, or the browser's override (tests and previews). Empty means Google is not set up. */
export function googleClientId(fromConfig: string): string {
  try { return localStorage.getItem("phiz-google-client-id") || fromConfig || ""; } catch { return fromConfig || ""; }
}

function loadGis(): Promise<void> {
  if ((window as unknown as { google?: Gis }).google?.accounts?.oauth2) return Promise.resolve();
  loading ??= new Promise<void>((ok, fail) => {
    const s = document.createElement("script");
    s.src = GIS; s.async = true;
    s.onload = () => ok();
    s.onerror = () => { loading = null; fail(new Error("gis")); };
    document.head.appendChild(s);
  });
  return loading;
}

async function accessToken(clientId: string): Promise<string> {
  if (token && token.until > Date.now()) return token.value;
  await loadGis();
  const g = (window as unknown as { google: Gis }).google;
  const value = await new Promise<string>((ok, fail) => {
    g.accounts.oauth2.initTokenClient({
      client_id: clientId, scope: SCOPE,
      callback: r => (r.access_token ? ok(r.access_token) : fail(new Error(r.error || "no token"))),
      error_callback: e => fail(e instanceof Error ? e : new Error("sign-in closed")),
    }).requestAccessToken();
  });
  token = { value, until: Date.now() + 50 * 60_000 };
  return value;
}

/* Uploads the deck as a Google Slides presentation and returns its address. */
export async function toGoogleSlides(clientId: string, deck: Blob, name: string): Promise<string> {
  const auth = await accessToken(clientId);
  const meta = { name: name.replace(/\.pptx$/i, ""), mimeType: "application/vnd.google-apps.presentation" };
  const body = new FormData();
  body.append("metadata", new Blob([JSON.stringify(meta)], { type: "application/json" }));
  body.append("file", new Blob([deck], { type: "application/vnd.openxmlformats-officedocument.presentationml.presentation" }), name);
  const r = await fetch(UPLOAD, { method: "POST", headers: { Authorization: `Bearer ${auth}` }, body });
  if (r.status === 401) token = null;
  if (!r.ok) throw new Error(`Drive ${r.status}`);
  const { id } = (await r.json()) as { id: string };
  return `https://docs.google.com/presentation/d/${encodeURIComponent(id)}/edit`;
}
