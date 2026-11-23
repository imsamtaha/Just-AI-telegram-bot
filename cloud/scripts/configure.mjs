// Local only. Generate a gitignored server-side module; never print credentials.
import { readFileSync, writeFileSync, chmodSync } from 'node:fs';
const source = readFileSync('.env', 'utf8');
const values = {};
for (const raw of source.split(/\r?\n/)) {
  const line = raw.trim();
  if (!line || line.startsWith('#')) continue;
  const match = line.match(/^([A-Z_]+)\s*=\s*(.*)$/);
  if (!match) throw new Error('Invalid .env line; expected NAME=value');
  let value = match[2];
  if (/^["']/.test(value)) {
    if (value.at(-1) !== value[0]) throw new Error('Unclosed quote in .env');
    value = value.slice(1, -1);
  }
  if (/[<>\r\n]/.test(value)) throw new Error('Remove angle brackets and line breaks from values');
  values[match[1]] = value;
}
const provider = values.AI_PROVIDER || 'claude';
if (!['claude', 'openai'].includes(provider)) throw new Error('AI_PROVIDER must be claude or openai');
const prefix = provider === 'claude' ? 'ANTHROPIC' : 'OPENAI';
const apiKey = values[`${prefix}_API_KEY`];
const model = values[`${prefix}_MODEL`];
if (!apiKey || !model || /YOUR_|replace_me/.test(apiKey)) throw new Error('Set a real API key and model in .env');
const config = { provider, apiKey, model, systemPrompt: values.BOT_SYSTEM_PROMPT || "You are Just AI. Reply in the user's language. Never invent prices, actions, or completed trades." };
writeFileSync('tgcloud/lib/private_config.js', `// Generated locally. Do not commit. Server-side only.\nexport default ${JSON.stringify(config)};\n`, {mode:0o600});
chmodSync('tgcloud/lib/private_config.js', 0o600);
console.log('Server-side configuration generated; credentials were not printed.');
