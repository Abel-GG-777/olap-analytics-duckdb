import {build} from 'esbuild';
import {cp, mkdir, readFile, writeFile, readdir, stat} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';

await mkdir('dist/assets', {recursive:true});
await cp('web/data', 'dist/data', {recursive:true});
let html = await readFile('app/static/index.html', 'utf8');
html = html.replace('/static/style.css','/assets/style.css')
  .replace('<script src="/static/app.js" defer></script>', '<script type="module" src="/assets/app.js"></script>')
  .replace('DUCKDB · OLAP LAB','DUCKDB-WASM · OLAP LAB')
  .replace('<a href="/docs">Explorar la API ↗</a>', '<span>Consultas SQL en tu navegador · Cloudflare Pages</span>');
await writeFile('dist/index.html',html);
await cp('app/static/style.css','dist/assets/style.css');
await build({entryPoints:['web/main.js'],outfile:'dist/assets/app.js',bundle:true,
  format:'esm',platform:'browser',target:'es2022',minify:true});
for (const flavor of ['eh','mvp']) {
  const source='node_modules/@duckdb/duckdb-wasm/dist/';
  await cp(`${source}duckdb-browser-${flavor}.worker.js`,`dist/assets/duckdb-browser-${flavor}.worker.js`);
  // Cloudflare Pages limits each file to 25 MiB. Decompress in the browser.
  const wasm=await readFile(`${source}duckdb-${flavor}.wasm`);
  await writeFile(`dist/assets/duckdb-${flavor}.wasm.gz`,gzipSync(wasm,{level:9}));
}
await writeFile('dist/_headers', '/assets/*\n  Cache-Control: public, max-age=3600\n/data/*\n  Cache-Control: public, max-age=0, must-revalidate\n');
async function inspect(dir) {
  for(const entry of await readdir(dir,{withFileTypes:true})) {
    const path=`${dir}/${entry.name}`;
    if(entry.isDirectory()) await inspect(path);
    else {
      const {size}=await stat(path);
      if(size>25*1024*1024) throw new Error(`${path} supera 25 MiB`);
      console.log(`${path}: ${(size/1024/1024).toFixed(2)} MiB`);
    }
  }
}
await inspect('dist');
