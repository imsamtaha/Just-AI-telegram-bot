import { api } from 'sdk';
import handleMessage from './message.js';
import { createCallbackHandler } from '../lib/access.js';
export default createCallbackHandler({api,handleMessage});
