const usageData = [
  { day:"14 Aug", prompt:184000, output:21000, cached:74000 }, { day:"15 Aug", prompt:209000, output:26000, cached:96000 },
  { day:"16 Aug", prompt:171000, output:19000, cached:68000 }, { day:"17 Aug", prompt:236000, output:29000, cached:121000 },
  { day:"18 Aug", prompt:248000, output:31000, cached:137000 }, { day:"19 Aug", prompt:221000, output:27000, cached:116000 },
  { day:"20 Aug", prompt:194000, output:23000, cached:108000 },
];
const activities = [
  { name:"Cross-document reasoning", tokens:612000 }, { name:"Field gap filling", tokens:438000 },
  { name:"Quality assessment", tokens:241000 }, { name:"Decision summary", tokens:162000 }, { name:"Semantic normalization", tokens:120000 },
];
const cases = [
  ["CASE-1842","PAFN","Cross-document reasoning","gpt-4.1",18420,2180,11200,20600,0.143,1840],
  ["CASE-1841","PAFN","Field gap filling","gpt-4.1-mini",8420,930,5100,9350,0.031,960],
  ["CASE-1840","Customs","Cross-document reasoning","gpt-4.1",29400,3610,14400,33010,0.231,2580],
  ["CASE-1839","PAFN","Quality assessment","gpt-4.1",6240,510,0,6750,0.049,1120],
  ["CASE-1838","PAFN","Decision summary","gpt-4.1-mini",3190,620,2048,3810,0.014,740],
  ["CASE-1837","Customs","Semantic normalization","gpt-4.1-mini",4770,480,2800,5250,0.018,810],
  ["CASE-1836","PAFN","Cross-document reasoning","gpt-4.1",15900,1970,9800,17870,0.124,1690],
  ["CASE-1835","PAFN","Field gap filling","gpt-4.1-mini",7380,840,4200,8220,0.028,890],
];
const rates = { "gpt-4.1": { input: 0.005, output: 0.015 }, "gpt-4.1-mini": { input: 0.0004, output: 0.0016 } };
const $ = selector => document.querySelector(selector);
const formatTokens = value => value >= 1e6 ? `${(value/1e6).toFixed(2)}M` : `${Math.round(value/1000)}K`;

function render() {
  const prompt = usageData.reduce((sum,d)=>sum+d.prompt,0), output = usageData.reduce((sum,d)=>sum+d.output,0), cached = usageData.reduce((sum,d)=>sum+d.cached,0);
  const total = prompt + output, cacheRate = Math.round(cached/prompt*100), cost = cases.reduce((sum,row)=>sum+row[8],0);
  $("#totalTokens").textContent = formatTokens(total); $("#totalCost").textContent = `$${cost.toFixed(2)}`;
  $("#avgTokens").textContent = formatTokens(total/148); $("#caseCount").textContent = "148 processed cases";
  $("#cacheRate").textContent = `${cacheRate}%`; $("#cachedTokens").textContent = `${formatTokens(cached)} input tokens reused`;
  $("#tokenTrend").textContent = "↓ 8.4% per case vs prior period";
  renderChart(); renderActivities(); renderEfficiency(prompt,output,cached); renderAnomalies(); renderCases(cases);
}
function renderChart(){ const max=Math.max(...usageData.map(d=>d.prompt+d.output)); $("#usageChart").innerHTML=usageData.map(d=>`<div class="day-column" title="${d.day}: ${formatTokens(d.prompt+d.output)} total"><div class="bar-stack" style="height:${Math.round((d.prompt+d.output)/max*180)}px"><span class="bar-prompt" style="height:${d.prompt/(d.prompt+d.output)*100}%"></span><span class="bar-output" style="height:${d.output/(d.prompt+d.output)*100}%"></span><span class="bar-cache" style="height:${Math.max(3,d.cached/d.prompt*22)}px"></span></div><small>${d.day}</small></div>`).join(""); }
function renderActivities(){ const max=activities[0].tokens; $("#activityList").innerHTML=activities.map(a=>`<div><div class="activity-head"><strong>${a.name}</strong><span>${formatTokens(a.tokens)}</span></div><div class="activity-track"><span style="width:${a.tokens/max*100}%"></span></div></div>`).join(""); }
function renderEfficiency(prompt,output,cached){ const score=78; $("#efficiencyValue").textContent=`${score}%`; $("#efficiencyRing").style.background=`conic-gradient(var(--pine) 0 ${score}%, #e8eeeb ${score}%)`; $("#cacheFact").textContent=`${Math.round(cached/prompt*100)}% of input`; $("#outputRatio").textContent=`${(output/(prompt+output)*100).toFixed(1)}% of total`; $("#highestActivity").textContent=activities[0].name; }
function renderAnomalies(){ const anomalies=[{title:"CASE-1840 · 1.9× baseline",body:"Cross-document reasoning used 33K tokens. Twelve documents were included in the bundle."},{title:"Cache miss increase",body:"Quality assessment cache reuse dropped below 10% for the Customs template."}]; $("#anomalyCount").textContent=anomalies.length; $("#anomalyList").innerHTML=anomalies.map(a=>`<article class="anomaly"><strong>${a.title}</strong><p>${a.body}</p></article>`).join(""); }
function renderCases(rows){ $("#caseRows").innerHTML=rows.map(row=>`<tr><td class="case-link">${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td><td><span class="model-tag">${row[3]}</span></td><td class="numeric">${row[4].toLocaleString()}</td><td class="numeric">${row[5].toLocaleString()}</td><td class="numeric">${row[6].toLocaleString()}</td><td class="numeric ${row[7]>25000?'high-usage':''}">${row[7].toLocaleString()}</td><td class="numeric">$${row[8].toFixed(3)}</td><td class="numeric">${row[9].toLocaleString()} ms</td></tr>`).join(""); $("#visibleRows").textContent=`${rows.length} cases`; }
$("#caseSearch").addEventListener("input", event=>{ const query=event.target.value.toLowerCase(); renderCases(cases.filter(row=>row.slice(0,4).some(value=>String(value).toLowerCase().includes(query)))); });
$("#tenantFilter").addEventListener("change", event=>{ const value=event.target.value; renderCases(cases.filter(row=>value==="all"||row[1].toLowerCase()===value)); });
$("#periodFilter").addEventListener("change", render);
$("#exportButton").addEventListener("click",()=>{ const csv=["case,tenant,activity,model,input,output,cached,total,cost,latency",...cases.map(row=>row.join(","))].join("\n"); const link=document.createElement("a"); link.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"})); link.download="aria-token-usage.csv"; link.click(); URL.revokeObjectURL(link.href); });
render();