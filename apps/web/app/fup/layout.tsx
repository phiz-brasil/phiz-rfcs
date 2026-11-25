import { AuthScript } from "../../components/AuthScript";
import "../themes/themes.css";

/* The FUP pages keep the look of the 2026-11-24 prototype (docs/spec/v2/fup.md): Space Grotesk and Inter load only here. */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AuthScript />
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap" />
      <meta name="robots" content="noindex" />
      {children}
    </>
  );
}
