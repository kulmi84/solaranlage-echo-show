import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {registry} from './registry.mjs';
test('separate SQLite registry supports update, stable paging and removal', async()=>{
  const db=new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('./schema.sql',import.meta.url),'utf8'));
  const store=registry({WIDGET_DB:{prepare(sql){return {bind(...args){return {
    first:async()=>db.prepare(sql).get(...args),run:async()=>db.prepare(sql).run(...args),
    all:async()=>({results:db.prepare(sql).all(...args)})};}};}}});
  await store.put('device:a',JSON.stringify({value:1}));
  await store.put('device:b',JSON.stringify({value:2}));
  await store.put('device:a',JSON.stringify({value:3}));
  assert.deepEqual(await store.get('device:a'),{value:3});
  const first=await store.list({prefix:'device:',limit:1});
  assert.equal(first.list_complete,false);
  const second=await store.list({prefix:'device:',limit:1,cursor:first.cursor});
  assert.equal(second.keys[0].name,'device:b');
  assert.equal(second.list_complete,true);
  await store.delete('device:a');
  assert.equal(await store.get('device:a'),null);
  db.close();
});
