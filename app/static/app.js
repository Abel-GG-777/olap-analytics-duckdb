const $ = id => document.getElementById(id);
const money = value => new Intl.NumberFormat('es-PE', {style:'currency',currency:'PEN',maximumFractionDigits:2}).format(value);
const number = value => new Intl.NumberFormat('es-PE').format(value);
function element(tag, text, className) {
  const el = document.createElement(tag); if (text !== undefined) el.textContent = text;
  if (className) el.className = className; return el;
}
async function load(event) {
  if (event) event.preventDefault();
  const button = document.querySelector('button'); button.disabled = true;
  $('status').textContent = 'Consultando DuckDB…'; $('results').hidden = true;
  const params = new URLSearchParams();
  for (const [key,value] of new FormData($('filters'))) if (value) params.set(key,value);
  try {
    const response = await fetch('/api/analytics?' + params);
    if (!response.ok) throw new Error(response.status === 422 ? 'Revisa el rango de fechas y los filtros.' : 'No se pudo consultar el servidor.');
    const data = await response.json(), s = data.summary;
    $('revenue').textContent = money(s.revenue); $('margin').textContent = number(Number(s.margin.toFixed(2))) + ' %';
    $('profit').textContent = money(s.profit) + ' de utilidad bruta'; $('orders').textContent = number(s.orders);
    $('units').textContent = number(s.units) + ' unidades vendidas'; $('average').textContent = money(s.average_order);
    $('trend').replaceChildren(); const max = Math.max(...data.trend.map(r=>r.revenue),1);
    for (const row of data.trend) {
      const col = element('div',undefined,'period'), bar = element('div',undefined,'bar');
      bar.style.height = (row.revenue/max*175)+'px'; col.title = `${row.period}: ${money(row.revenue)}`;
      col.append(bar,element('small',row.period.slice(0,7))); $('trend').append(col);
    }
    $('groups').replaceChildren();
    for (const row of data.groups) {
      const group = element('div',undefined,'group'), label = element('div',undefined,'group-label');
      label.append(element('span',row.label),element('strong',money(row.revenue)));
      const track = element('div',undefined,'track'), fill = element('div',undefined,'fill');
      fill.style.width = (s.revenue ? row.revenue/s.revenue*100 : 0)+'%'; track.append(fill); group.append(label,track); $('groups').append(group);
    }
    $('rollup').replaceChildren();
    for (const row of data.rollup) {
      const tr = element('tr',undefined,row.category_total ? 'subtotal' : '');
      tr.append(element('td',row.city_total ? 'Total general' : row.city),element('td',row.category_total ? 'Todas' : row.category),element('td',money(row.revenue),'number')); $('rollup').append(tr);
    }
    $('status').textContent = s.orders ? `${number(s.orders)} pedidos en la selección · ${data.dataset}` : 'Sin ventas en esta selección. Prueba otro período o cambia los filtros.';
    $('results').hidden = false;
  } catch (error) { $('status').textContent = error.message + ' Puedes volver a intentar.'; }
  finally { button.disabled = false; }
}
$('filters').addEventListener('submit', load); load();
