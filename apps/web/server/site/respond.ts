/* Route handlers answer with the generated page as HTML. */
export const html = (body: string) => new Response(body, { headers: { "content-type": "text/html; charset=utf-8" } });
