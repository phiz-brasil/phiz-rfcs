"use client";
import type { ReactNode } from "react";
import { pick, t, type Lang, type Tri } from "../lib/i18n";
import { DbError } from "../lib/db";

/* A text people wrote: in the reader's language, or in another one with a small tag saying which. */
export function Said({ value, lang }: { value: Tri | null | undefined; lang: Lang }) {
  const { text, from } = pick(value, lang);
  if (!text) return null;
  return <>{text}{from ? <span className="from" title={`${t("fromLang", lang)} ${from}`}>{from.toUpperCase()}</span> : null}</>;
}

export function StatusBadge({ status, lang }: { status: string; lang: Lang }) {
  return <span className="badge" data-s={status}>{t(`status.${status}`, lang)}</span>;
}

export const message = (e: unknown, lang: Lang) => (e instanceof DbError && e.code === "rate" ? t("rate", lang) : t("error", lang));

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

export const dateText = (d: string | null) => (d ? d.slice(0, 10) : "—");
