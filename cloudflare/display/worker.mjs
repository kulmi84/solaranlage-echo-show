import {sessionRoute} from './sessions.mjs';
import {widgetImageRoute} from './widget-images.mjs';
export default {async fetch(request,env){return await widgetImageRoute(request,env)||await sessionRoute(request,env)||new Response('Not found',{status:404});}};
