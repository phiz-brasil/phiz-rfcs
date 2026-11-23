"use client";
/* The frame of the React pages: the brand, the links of the site, the language buttons and the name of the person who edits (typed once,
   remembered in the browser; there is no sign-in yet). */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { LANGS, T, useLang, type Lang } from "../lib/i18n";
import { client, type Db, type Supabase } from "../lib/db";

type Ctx = { lang: Lang; db: Db; name: string; setName: (n: string) => void };
const Context = createContext<Ctx | null>(null);
export const useApp = () => {
  const c = useContext(Context);
  if (!c) throw new Error("outside <Shell>");
  return c;
};

const NAME_KEY = "phiz-rfc-author";                 // the same key the comments and the status picker use

export function Shell({ supabase, children }: { supabase: Supabase; children: ReactNode }) {
  const [lang, setLang] = useLang();
  const [name, setNameState] = useState("");
  const [db] = useState(() => client(supabase));
  useEffect(() => { try { setNameState(localStorage.getItem(NAME_KEY) ?? ""); } catch { /* blocked */ } }, []);
  const setName = (n: string) => { setNameState(n); try { localStorage.setItem(NAME_KEY, n); } catch { /* blocked */ } };
  return (
    <Context.Provider value={{ lang, db, name, setName }}>
      <header>
        <div className="wrap">
          <div className="brand"><span className="logo" aria-hidden="true">P</span><span>PHIZCHAT</span></div>
          <div className="hright">
            <a className="navc" href="/">{T.rfcs[lang]}</a>
            <a className="navc" href="/themes/" aria-current="page">{T.themes[lang]}</a>
            <a className="navc" href="/comments/">💬 {T.comments[lang]}</a>
            <label className="who"><span>{T.yourName[lang]}</span><input value={name} maxLength={60} autoComplete="name" onChange={e => setName(e.target.value)} /></label>
            <div className="langs" role="group" aria-label="Language">
              {LANGS.map(l => (
                <button key={l} type="button" aria-pressed={l === lang} onClick={() => setLang(l)}>{l === "pt" ? "PT-BR" : l === "en" ? "EN-US" : "中文"}</button>
              ))}
            </div>
          </div>
        </div>
      </header>
      <main className="wrap">{children}</main>
    </Context.Provider>
  );
}
