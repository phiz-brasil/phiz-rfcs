/* What used to live under an RFC's old address (/rfcs/PHZ-0001/v1.0.html, /rfcs/PHZ-0001/openapi/, openapi.en.yaml, mocks/…) is now an attachment
   of the theme (phase 8): every such address leads to the attachments of the theme. */
export function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  return params.then(({ id }) => {
    if (!/^PHZ-\d{4}$/.test(id)) return new Response("Not found", { status: 404 });
    return new Response(null, { status: 308, headers: { location: `/themes/${id}/#attachments` } });
  });
}
