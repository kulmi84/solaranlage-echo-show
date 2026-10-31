// Loopback-only transport fixture. Never deployed or imported by the Worker.
import { createServer } from 'node:http';
import worker from './worker.mjs';
import { environment } from './enrollment-fixture.mjs';
const env = environment();
const server = createServer(async (incoming, outgoing) => {
  try {
    const chunks = [];
    for await (const chunk of incoming) chunks.push(chunk);
    const request = new Request('https://fixture.example' + incoming.url, {
      method: incoming.method,
      headers: { ...incoming.headers, 'CF-Connecting-IP': '192.0.2.1' },
      ...(['GET', 'HEAD'].includes(incoming.method) ? {} : { body: Buffer.concat(chunks) }),
    });
    const result = await worker.fetch(request, env);
    outgoing.writeHead(result.status, Object.fromEntries(result.headers));
    outgoing.end(Buffer.from(await result.arrayBuffer()));
  } catch {
    outgoing.writeHead(500); outgoing.end('{}');
  }
});
server.listen(0, '127.0.0.1', () => console.log(server.address().port));
