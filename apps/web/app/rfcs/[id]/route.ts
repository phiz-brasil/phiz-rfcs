/* The old address of an RFC (/rfcs/PHZ-0001/) leads to its page in the database (/rfc/?id=PHZ-0001), keeping the rest of the query
   (?c=<comment>) after the id; the browser keeps the #hash. Whatever sat under it (v1.0.html, openapi/…) is an attachment now: see [...path]/route.ts. */
export function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  return params.then(({ id }) => {
    if (!/^PHZ-\d{4}$/.test(id)) return new Response("Not found", { status: 404 });
    const rest = new URL(request.url).search.replace(/^\?/, "");
    return new Response(null, { status: 308, headers: { location: `/rfc/?id=${id}${rest ? "&" + rest : ""}` } });
  });
}
