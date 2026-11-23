// Copy the migration into an existing tgcloud project without touching CLI state.
import { cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const source=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const target=resolve(process.argv[2]||'');
if(!process.argv[2]||target===source||!existsSync(join(target,'package.json')))throw new Error('Usage: node cloud/scripts/install.mjs /path/to/JustAI_chatbot');
const earlyIgnore=join(target,'.gitignore');
writeFileSync(earlyIgnore,(existsSync(earlyIgnore)?readFileSync(earlyIgnore,'utf8'):'')+'\njustai-backup-*/\n');
const stamp=new Date().toISOString().replace(/[:.]/g,'-');
const backup=join(target,`justai-backup-${stamp}`);mkdirSync(backup);
for(const name of ['tgcloud','package.json','package-lock.json'])if(existsSync(join(target,name)))cpSync(join(target,name),join(backup,name),{recursive:true});
// Refuse to overwrite another custom cloud app; only the known starter is replaced.
const handler=join(target,'tgcloud','handlers','message.js');
if(existsSync(handler)&&!readFileSync(handler,'utf8').includes('You said:'))throw new Error('Existing custom message handler detected. Backup created; merge the migration manually.');
for(const name of ['tgcloud','scripts','tests','docs'])cpSync(join(source,name),join(target,name),{recursive:true});
const pkg=JSON.parse(readFileSync(join(target,'package.json'),'utf8'));
pkg.type='module';pkg.devDependencies={...pkg.devDependencies,'@tgcloud/cli':'0.2.0'};
pkg.scripts={...pkg.scripts,'justai:test':'node --test tests/*.test.js','justai:configure':'node scripts/configure.mjs'};
writeFileSync(join(target,'package.json'),JSON.stringify(pkg,null,2)+'\n');
if(!existsSync(join(target,'.env')))cpSync(join(source,'.env.example'),join(target,'.env'));
const ignore=join(target,'.gitignore');const old=existsSync(ignore)?readFileSync(ignore,'utf8'):'';
writeFileSync(ignore,old+'\n.env\n.env.*\n!.env.example\n.tgcloud/\nnode_modules/\ntgcloud/lib/private_config.js\njustai-backup-*/\n');
console.log('Migration copied. CLI state preserved. Next: npm install, edit .env, npm run justai:configure. Nothing was deployed.');
