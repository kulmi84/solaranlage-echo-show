import {sessionRoute} from './sessions.mjs';
export default {async fetch(request,env){return await sessionRoute(request,env)||new Response('Not found',{status:404});}};
