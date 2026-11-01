import {test,expect} from '@playwright/test';

test('DuckDB-Wasm calculates totals, filters, rollup, grain and empty selections',async({page})=>{
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('#status')).toContainText('60', {timeout:90000});
  await expect(page.locator('#results')).toBeVisible();
  const original=await page.locator('#revenue').innerText();
  const totals=await page.evaluate(async()=>globalThis.olapAnalytics(new URLSearchParams()));
  expect(totals.summary.orders).toBe(60000);
  expect(totals.summary.revenue).toBeCloseTo(22156502.75,2);
  expect(totals.summary.profit).toBeCloseTo(7189634.09,2);
  expect(totals.trend).toHaveLength(24);
  expect(totals.rollup.find(r=>r.city_total===1).revenue).toBeCloseTo(totals.summary.revenue,2);
  await page.getByLabel('Ciudad',{exact:true}).selectOption('Lima');
  await page.getByRole('button',{name:'Explorar datos'}).click();
  await expect(page.locator('#status')).toContainText('15');
  await expect(page.locator('#revenue')).not.toHaveText(original);
  const lima=await page.evaluate(async()=>globalThis.olapAnalytics(new URLSearchParams({city:'Lima',grain:'quarter'})));
  expect(lima.summary.orders).toBe(15050);
  expect(lima.trend).toHaveLength(8);
  await page.getByLabel('Desde',{exact:true}).fill('2030-01-01');
  await page.getByLabel('Hasta',{exact:true}).fill('2030-12-31');
  await page.getByRole('button',{name:'Explorar datos'}).click();
  await expect(page.locator('#status')).toContainText('Sin ventas');
  await expect(page.locator('#orders')).toHaveText('0');
  expect(errors).toEqual([]);
});

test('mobile layout fits the viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await expect(page.locator('#results')).toBeVisible({timeout:90000});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await expect(page.getByRole('button',{name:'Explorar datos'})).toBeEnabled();
});
