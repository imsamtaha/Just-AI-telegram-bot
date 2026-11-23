import { api, fetch, db } from 'sdk';
import config from '../lib/private_config.js';
import { createStore } from '../lib/store.js';
import { createHandler } from '../lib/core.js';
export default createHandler({api,fetch,store:createStore(db),config});
