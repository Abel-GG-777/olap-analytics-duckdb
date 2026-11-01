import * as duckdb from '@duckdb/duckdb-wasm';

let engine;
async function initialize() {
  const bundles={};
  for(const flavor of ['mvp','eh']) bundles[flavor]={
    mainModule:`/assets/duckdb-${flavor}.wasm.gz`,
    mainWorker:`/assets/duckdb-browser-${flavor}.worker.js`,
  };
  const bundle=await duckdb.selectBundle(bundles);
  const compressed=await fetch(bundle.mainModule);
  if(!compressed.ok) throw new Error('No se pudo descargar DuckDB.');
  const bytes=await new Response(compressed.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const moduleURL=URL.createObjectURL(new Blob([bytes],{type:'application/wasm'}));
  const worker=new Worker(bundle.mainWorker);
  const db=new duckdb.AsyncDuckDB(new duckdb.VoidLogger(),worker);
  try { await db.instantiate(moduleURL); } finally { URL.revokeObjectURL(moduleURL); }
  const conn=await db.connect();
  for(const table of ['fact_sales','dim_city','dim_category','dim_date']) {
    const response=await fetch(`/data/${table}.parquet`);
    if(!response.ok) throw new Error('No se pudo descargar el dataset.');
    await db.registerFileBuffer(`${table}.parquet`,new Uint8Array(await response.arrayBuffer()));
    await conn.query(`CREATE TABLE ${table} AS SELECT * FROM '${table}.parquet'`);
  }
  await conn.query(`CREATE VIEW sales AS SELECT f.*, c.city,p.category,d.year,d.quarter,d.month
    FROM fact_sales f JOIN dim_city c ON f.city_id=c.id
    JOIN dim_category p ON f.category_id=p.id JOIN dim_date d ON f.date=d.date`);
  const manifest=await (await fetch('/data/manifest.json')).json();
  return {db,conn,manifest};
}

function normalize(table) {
  // Explicit DOUBLE casts below avoid Arrow decimal / BigInt representation ambiguity.
  return table.toArray().map(row=>Object.fromEntries(Object.entries(row.toJSON()).map(([k,v])=>[k,typeof v==='bigint'?Number(v):v])));
}

export async function analytics(params) {
  const start=params.get('start') || '2024-01-01', end=params.get('end') || '2025-12-31';
  if(!/^\d{4}-\d{2}-\d{2}$/.test(start) || !/^\d{4}-\d{2}-\d{2}$/.test(end) || start>end) throw new Error('Revisa el rango de fechas.');
  const dimension=params.get('dimension') || 'city', grain=params.get('grain') || 'month';
  if(!['city','category','channel'].includes(dimension) || !['month','quarter','year'].includes(grain)) throw new Error('Agrupación inválida.');
  if(!engine) engine=initialize().catch(error=>{engine=undefined;throw error;});
  const {conn,manifest}=await engine;
  const values=[start,end]; let where='date BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)';
  const allowed={city:['Lima','Arequipa','Cusco','Trujillo'],category:['Tecnología','Hogar','Moda','Deportes'],channel:['Web','Tienda']};
  for(const [key,options] of Object.entries(allowed)) {
    const value=params.get(key);
    if(value) {
      if(!options.includes(value)) throw new Error('Filtro inválido.');
      where+=` AND ${key} = ?`; values.push(value);
    }
  }
  const base=`FROM sales WHERE ${where}`;
  async function query(sql) {
    const stmt=await conn.prepare(sql);
    try {return normalize(await stmt.query(...values));} finally {await stmt.close();}
  }
  const summary=(await query(`SELECT count(*)::DOUBLE AS orders,coalesce(sum(units),0)::DOUBLE AS units,
    coalesce(sum(revenue),0)::DOUBLE AS revenue,coalesce(sum(revenue-cost),0)::DOUBLE AS profit,
    coalesce(avg(revenue),0)::DOUBLE AS average_order,
    coalesce(100*sum(revenue-cost)/nullif(sum(revenue),0),0)::DOUBLE AS margin ${base}`))[0];
  const groups=await query(`SELECT ${dimension} AS label,count(*)::DOUBLE AS orders,
    sum(revenue)::DOUBLE AS revenue,sum(revenue-cost)::DOUBLE AS profit ${base}
    GROUP BY ${dimension} ORDER BY revenue DESC,label`);
  const trend=await query(`WITH periods AS (SELECT date_trunc('${grain}',date)::DATE AS period,
    sum(revenue)::DOUBLE AS revenue ${base} GROUP BY 1)
    SELECT period::VARCHAR AS period,revenue,revenue-lag(revenue) OVER (ORDER BY period) AS change FROM periods ORDER BY period`);
  const rollup=await query(`SELECT city,category,grouping(city)::DOUBLE AS city_total,
    grouping(category)::DOUBLE AS category_total,sum(revenue)::DOUBLE AS revenue ${base}
    GROUP BY ROLLUP(city,category) ORDER BY city NULLS LAST,category NULLS LAST`);
  return {summary,groups,trend,rollup,dataset:manifest.version,currency:'PEN'};
}
