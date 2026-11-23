/* The pages of phase 1 are route handlers that answer with the generated HTML (server/site/pages.ts); this layout only frames the
   pages Next.js draws itself, such as "not found". */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
