#!/usr/bin/env node
// Parse/transpile only. No native APIs execute, and this is not a dependency-aware typecheck.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ts=require('typescript');const root=path.resolve(__dirname,'..');
const results=[];
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else if(/\.(mjs|js|cjs|ts|tsx|jsx)$/.test(p)){
 const relative=path.relative(root,p);let code=fs.readFileSync(p,'utf8');let diagnostics=[];
 if(/\.jsx$/.test(p)) code=code.replace(/^#target.*$/gm,'');
 if(/\.(tsx?|jsx)$/.test(p)){
  const r=ts.transpileModule(code,{fileName:p,reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
  diagnostics=(r.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).map(x=>ts.flattenDiagnosticMessageText(x.messageText,' '));
 }else{
  // TypeScript's parser accepts modules; report parse diagnostics without resolving third-party packages.
  const parsed=ts.createSourceFile(p,code,ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
  diagnostics=parsed.parseDiagnostics.map(x=>ts.flattenDiagnosticMessageText(x.messageText,' '));
 }
 results.push({file:relative,status:diagnostics.length?'FAIL':'SYNTAX_PASS',diagnostics});
}}}
walk(path.join(root,'phenoDesign-overlay'));walk(path.join(root,'worker-recipes'));
console.log(JSON.stringify({scope:'syntax/transpile only, not native execution or module/type resolution',typescript:ts.version,results},null,2));
if(results.some(x=>x.status==='FAIL'))process.exitCode=1;
