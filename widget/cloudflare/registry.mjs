// A separate D1 database avoids Workers KV's daily list-operation limit at a one-minute interval.
export function registry(env) {
  if (env.REGISTRATIONS) return env.REGISTRATIONS; // injected in isolated unit tests
  return {
    async get(key) {
      const row = await env.WIDGET_DB.prepare('SELECT value FROM widget_registrations WHERE key=?').bind(key).first();
      return row ? JSON.parse(row.value) : null;
    },
    async put(key, value) {
      await env.WIDGET_DB.prepare('INSERT INTO widget_registrations(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').bind(key,value).run();
    },
    async delete(key) {
      await env.WIDGET_DB.prepare('DELETE FROM widget_registrations WHERE key=?').bind(key).run();
    },
    async list({prefix,limit=100,cursor=''}) {
      const result = await env.WIDGET_DB.prepare('SELECT key AS name FROM widget_registrations WHERE key LIKE ? AND key>? ORDER BY key LIMIT ?').bind(prefix+'%',cursor,limit+1).all();
      const keys = result.results.slice(0,limit);
      return {keys,list_complete:result.results.length<=limit,cursor:keys.at(-1)?.name};
    }
  };
}
