import {readFileSync} from 'node:fs';
import {fullscreen, fixed} from './fullscreen.mjs';
const input = JSON.parse(readFileSync(process.argv[2], 'utf8').replace(/^\uFEFF/, ''));
console.log(JSON.stringify({fullscreen: fullscreen(input.row, input.now),
  numbers: input.numbers.map(([v, digits, grouping]) => fixed(v, digits, grouping))}));
