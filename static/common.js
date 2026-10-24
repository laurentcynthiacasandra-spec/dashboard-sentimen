const COL={Positif:'#2e7d32',Negatif:'#c62828'};
const APPCOL={Instagram:'#8e44ad',TikTok:'#16a085',X:'#34495e'};
const fmt=n=>Number(n).toLocaleString('id-ID');
async function api(u,opt){const r=await fetch(u,opt);if(r.status===401){location='/login';return}const j=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(new Error(j.error||r.statusText),{status:r.status});return j}
const charts={};
function draw(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg)}
Chart.defaults.font.family='system-ui,-apple-system,"Segoe UI",Roboto,sans-serif';Chart.defaults.maintainAspectRatio=false;
function opts(o){return fill(o)}
function fill(sel,items,all){sel.innerHTML=(all?`<option value="">${all}</option>`:'')+items.map(i=>`<option value="${i.id}">${i.nama}</option>`).join('')}
