// Local test fixture only; never imported by the deployed Worker.
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
export function environment({ schema = true } = {}) {
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('./schema.sql', import.meta.url), 'utf8'));
  if (schema) db.exec(readFileSync(new URL('./enrollment-schema.sql', import.meta.url), 'utf8'));
  let tail = Promise.resolve();
  const prepare = sql => ({ bind(...args) {
    return {
      first: async () => db.prepare(sql).get(...args) || null,
      all: async () => ({ results: db.prepare(sql).all(...args) }),
      run: async () => ({ meta: { changes: Number(db.prepare(sql).run(...args).changes) } }),
    };
  } });
  return {
    raw: db, DB: { prepare, batch(statements) {
      // D1 serializes transactional batches. Retain real SQL predicates/rollback.
      const work = tail.then(async () => {
        db.exec('BEGIN');
        try { const result = []; for (const s of statements) result.push(await s.run()); db.exec('COMMIT'); return result; }
        catch (error) { db.exec('ROLLBACK'); throw error; }
      });
      tail = work.catch(() => {}); return work;
    } },
    PUBLIC_ENROLLMENT_ENABLED: 'true', REGISTRATION_KEY: 'local-fixture-key-'.repeat(4),
    SIGNUP_LIMITER: { calls: [], async limit(input) { this.calls.push(input); return { success: true }; } },
    LIMITER: { calls: 0, async limit() { this.calls++; return { success: true }; } },
    ADMIN_TOKEN: 'admin'.repeat(16), OAUTH_CLIENT_ID: 'fixture-client',
    OAUTH_CLIENT_SECRET: 'fixture-oauth-secret',
    OAUTH_REDIRECT_URIS: '["https://alexa.amazon.de/api/skill/link/fixture"]',
  };
}
