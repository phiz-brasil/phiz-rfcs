"use client";
/* The sign-in page (docs/spec/v2/login.md): the e-mail of the company, a link and a 6-digit code in one message. The work is done by assets/auth.js (window.PHIZ_AUTH). */
import { useEffect, useRef, useState } from "react";
import { LANGS, T, useLang } from "../lib/i18n";

type Auth = {
  member(email: string): boolean;
  sendLink(email: string): Promise<void>;
  verify(email: string, code: string): Promise<unknown>;
  fromAddress(): Promise<unknown | null>;
  nextPath(raw: string | null): string;
};
const auth = () => (window as unknown as { PHIZ_AUTH?: Auth }).PHIZ_AUTH;

export function LoginPage() {
  const [lang, setLang] = useLang();
  const [email, setEmail] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const next = () => auth()?.nextPath(new URLSearchParams(location.search).get("next")) ?? "/overview/";

  // the link of the message brings the tokens back in the address
  useEffect(() => {
    if (!location.hash.includes("access_token")) return;
    setBusy(true);
    auth()?.fromAddress().then(s => { if (s) location.replace(next()); else setBusy(false); })
      .catch(() => { setError(T.loginDomain[lang]); setBusy(false); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const countdown = () => {
    setWait(30);
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => setWait(w => { if (w <= 1 && timer.current) clearInterval(timer.current); return Math.max(0, w - 1); }), 1000);
  };
  const send = async () => {
    const to = email.trim().toLowerCase();
    if (!auth()?.member(to)) return setError(T.loginDomain[lang]);
    setError("");
    setBusy(true);
    try { await auth()!.sendLink(to); setSentTo(to); setCode(""); countdown(); } catch { setError(T.loginFailed[lang]); }
    setBusy(false);
  };
  const enter = async () => {
    if (!sentTo) return;
    setError("");
    setBusy(true);
    try { await auth()!.verify(sentTo, code.trim()); location.replace(next()); }
    catch (e) { setError((e as { notMember?: boolean }).notMember ? T.loginDomain[lang] : T.loginBadCode[lang]); setBusy(false); }
  };

  return (
    <>
      <header className="appbar">
        <div className="wrap topbar">
          <span className="brand"><span className="mark">PHIZCHAT</span></span>
          <div className="tools">
            <div className="langs" role="group" aria-label="Language">
              {LANGS.map(l => <button key={l} type="button" aria-pressed={l === lang} onClick={() => setLang(l)}>{l === "pt" ? "PT-BR" : l === "en" ? "EN-US" : "中文"}</button>)}
            </div>
          </div>
        </div>
      </header>
      <main className="wrap page login">
        <p className="eyebrow">PHIZCHAT</p>
        <h1>{T.loginTitle[lang]}</h1>
        <p className="lead">{T.loginLead[lang]}</p>
        <form className="panel" onSubmit={e => { e.preventDefault(); void (sentTo ? enter() : send()); }} aria-label={T.loginTitle[lang]}>
          <label className="field"><span>{T.loginEmail[lang]}</span>
            <input type="email" autoComplete="email" value={email} disabled={!!sentTo} onChange={e => setEmail(e.target.value)} /></label>
          {sentTo ? (
            <>
              <p className="note" role="status">{T.loginSent[lang]} {sentTo}</p>
              <label className="field"><span>{T.loginCode[lang]}</span>
                <input inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ""))} /></label>
            </>
          ) : null}
          {error ? <p className="state err" role="alert">{error}</p> : null}
          <p>
            {sentTo ? (
              <>
                <button type="submit" className="btn primary" disabled={busy || code.length !== 6}>{T.loginEnter[lang]}</button>{" "}
                <button type="button" className="btn" disabled={busy || wait > 0} onClick={() => void send()}>{T.loginAgain[lang]}{wait > 0 ? ` (${wait})` : ""}</button>
              </>
            ) : <button type="submit" className="btn primary" disabled={busy}>{busy ? T.loginSending[lang] : T.loginSend[lang]}</button>}
          </p>
        </form>
      </main>
    </>
  );
}
