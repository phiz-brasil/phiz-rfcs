"use client";
/* The frame of the React pages: the brand, the links of the site, the language buttons and the name of the person who edits (typed once,
   remembered in the browser; there is no sign-in yet). */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { LANGS, T, useLang, type Lang } from "../lib/i18n";
import { client, type Db, type Supabase } from "../lib/db";

type Ctx = { lang: Lang; db: Db; name: string; setName: (n: string) => void; reader: boolean };
type Auth = { account(): { email: string; name: string | null } | null; signOut(): Promise<void> };
const auth = () => (typeof window !== "undefined" ? (window as unknown as { PHIZ_AUTH?: Auth }).PHIZ_AUTH : undefined);
const Context = createContext<Ctx | null>(null);
export const useApp = () => {
  const c = useContext(Context);
  if (!c) throw new Error("outside <Shell>");
  return c;
};

const NAME_KEY = "phiz-rfc-author";                 // the same key the comments and the status picker use
const READER_KEY = "phiz-reader";                   // reader mode: the controls to create and edit are hidden (a link with ?mode=reader opens in it)

export function Shell({ supabase, children }: { supabase: Supabase; children: ReactNode }) {
  const [lang, setLang] = useLang();
  const [name, setNameState] = useState("");
  const [db] = useState(() => client(supabase));
  const [reader, setReaderState] = useState(false);
  const [account, setAccount] = useState<{ email: string; name: string | null } | null>(null);     // the signed-in person (assets/auth.js); null before sign-in is required
  useEffect(() => {
    try { setNameState(localStorage.getItem(NAME_KEY) ?? ""); } catch { /* blocked */ }
    setAccount(auth()?.account() ?? null);
    const asked = new URLSearchParams(location.search).get("mode");
    if (asked === "reader" || asked === "edit") { setReaderState(asked === "reader"); return; }
    try { setReaderState(localStorage.getItem(READER_KEY) === "1"); } catch { /* blocked */ }
  }, []);
  const setReader = (on: boolean) => { setReaderState(on); try { localStorage.setItem(READER_KEY, on ? "1" : "0"); } catch { /* blocked */ } };
  const setName = (n: string) => { setNameState(n); try { localStorage.setItem(NAME_KEY, n); } catch { /* blocked */ } };
  return (
    <Context.Provider value={{ lang, db, name, setName, reader }}>
      <header className="appbar">
        <div className="wrap topbar">
          <a className="brand" href="/overview/" aria-label="PhizChat"><span className="mark">PHIZCHAT</span></a>
          <nav className="mainnav" aria-label={T.navMain[lang]}>
            <Menu label={T.eyebrowTrack[lang]} paths={["/overview/", "/executive/", "/fup/", "/board/", "/roadmap/", "/metrics/"]}>
              <NavLink href="/overview/">{T.overview[lang]}</NavLink>
              <NavLink href="/executive/">{T.executive[lang]}</NavLink>
              <NavLink href="/fup/">{T.fup[lang]}</NavLink>
              <NavLink href="/board/">{T.board[lang]}</NavLink>
              <NavLink href="/roadmap/">{T.roadmap[lang]}</NavLink>
              <NavLink href="/metrics/">{T.metrics[lang]}</NavLink>
            </Menu>
            <Menu label={T.eyebrowPortfolio[lang]} paths={["/themes/", "/slides/"]}>
              <NavLink href="/themes/">{T.themes[lang]}</NavLink>
              <NavLink href="/slides/">{T.slides[lang]}</NavLink>
            </Menu>
            <Menu label={T.navDocs[lang]} paths={["/attachments/", "/comments/", "/rfc/", "/nova/"]}>
              <NavLink href="/">{T.rfcs[lang]}</NavLink>
              <NavLink href="/attachments/">{T.attachments[lang]}</NavLink>
              <NavLink href="/comments/">{T.comments[lang]}</NavLink>
            </Menu>
          </nav>
          <Menu label={name.trim() || T.yourName[lang]} className="user" right aria={T.userMenu[lang]}>
            <div className="user-pop">
              {account ? (
                <div className="acct" data-account>
                  <span className="who-email">{account.email}</span>
                  <button type="button" className="toggle" onClick={async () => { await auth()?.signOut(); location.href = "/login/"; }}>{T.signOut[lang]}</button>
                </div>
              ) : !reader ? <label className="who"><span>{T.yourName[lang]}</span><input value={name} maxLength={60} autoComplete="name" placeholder={T.yourName[lang]} onChange={e => setName(e.target.value)} /></label> : null}
              <button type="button" className="toggle" aria-pressed={reader} onClick={() => setReader(!reader)}>{reader ? T.editor[lang] : T.reader[lang]}</button>
              <div className="langs" role="group" aria-label="Language">
                {LANGS.map(l => (
                  <button key={l} type="button" aria-pressed={l === lang} onClick={() => setLang(l)}>{l === "pt" ? "PT-BR" : l === "en" ? "EN-US" : "中文"}</button>
                ))}
              </div>
            </div>
          </Menu>
        </div>
      </header>
      <main className="wrap page">{children}</main>
    </Context.Provider>
  );
}

/* A link of the main menu, marked as the current page when the address is under it ("/" only on the home page itself). */
function NavLink({ href, children }: { href: string; children: ReactNode }) {
  const [here, setHere] = useState(false);
  useEffect(() => {
    const p = location.pathname;
    setHere(href === "/" ? p === "/" : p.startsWith(href));
  }, [href]);
  return <a className="navlink" href={href} aria-current={here ? "page" : undefined}>{children}</a>;
}

/* A menu that opens on click (and with the keyboard) and closes when you click elsewhere or press Escape. Its button is marked as the current
   section when the address is under one of `paths`. */
function Menu({ label, children, paths = [], className = "", right = false, aria }: { label: string; children: ReactNode; paths?: string[]; className?: string; right?: boolean; aria?: string }) {
  const [open, setOpen] = useState(false);
  const [here, setHere] = useState(false);
  useEffect(() => { setHere(paths.some(p => location.pathname.startsWith(p))); }, [paths]);
  useEffect(() => {
    if (!open) return;
    const close = (e: Event) => { if (!(e.target as Element).closest?.(".menu")) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("click", close); document.removeEventListener("keydown", esc); };
  }, [open]);
  return (
    <div className={`menu ${className}`}>
      <button type="button" className="navlink" aria-expanded={open} aria-label={aria} data-here={here ? "1" : undefined} onClick={() => setOpen(o => !o)}>{label} <span aria-hidden="true">▾</span></button>
      <div className={`menu-pop${right ? " right" : ""}`} hidden={!open}>{children}</div>
    </div>
  );
}
