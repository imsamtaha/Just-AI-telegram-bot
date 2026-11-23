import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

test('installer preserves local login state and configuration stays untracked',()=>{
  const root=mkdtempSync(join(tmpdir(),'justai-setup-'));
  try {
    const target=join(root,'starter');mkdirSync(join(target,'tgcloud','handlers'),{recursive:true});
    mkdirSync(join(target,'.tgcloud'));writeFileSync(join(target,'.tgcloud','sentinel'),'unchanged');
    writeFileSync(join(target,'package.json'),'{"scripts":{"existing":"echo existing"}}');
    writeFileSync(join(target,'tgcloud','handlers','message.js'),'// You said: starter');
    const install=spawnSync(process.execPath,[resolve('scripts/install.mjs'),target],{encoding:'utf8'});
    assert.equal(install.status,0,install.stderr);
    assert.equal(readFileSync(join(target,'.tgcloud','sentinel'),'utf8'),'unchanged');
    assert.equal(JSON.parse(readFileSync(join(target,'package.json'))).scripts.existing,'echo existing');
    writeFileSync(join(target,'.env'),"AI_PROVIDER=claude\nANTHROPIC_API_KEY='fake-test-secret'\nANTHROPIC_MODEL=test-model\n");
    const configure=spawnSync(process.execPath,['scripts/configure.mjs'],{cwd:target,encoding:'utf8'});
    assert.equal(configure.status,0,configure.stderr);assert.ok(!configure.stdout.includes('fake-test-secret'));
    assert.ok(existsSync(join(target,'tgcloud','lib','private_config.js')));
    assert.match(readFileSync(join(target,'.gitignore'),'utf8'),/tgcloud\/lib\/private_config\.js/);
    const second=spawnSync(process.execPath,[resolve('scripts/install.mjs'),target],{encoding:'utf8'});
    assert.notEqual(second.status,0);assert.match(second.stderr,/custom message handler/);
  }finally{rmSync(root,{recursive:true,force:true});}
});
test('configuration validates without executing shell substitutions',()=>{
  const target=mkdtempSync(join(tmpdir(),'justai-config-'));
  try{
    mkdirSync(join(target,'tgcloud','lib'),{recursive:true});
    writeFileSync(join(target,'.env'),'AI_PROVIDER=claude\nANTHROPIC_API_KEY=<bad>\nANTHROPIC_MODEL=m\n');
    const result=spawnSync(process.execPath,[resolve('scripts/configure.mjs')],{cwd:target,encoding:'utf8'});
    assert.notEqual(result.status,0);assert.equal(existsSync(join(target,'tgcloud','lib','private_config.js')),false);
  }finally{rmSync(target,{recursive:true,force:true});}
});
