/* Model selection, artifact availability and paired comparison; no synthetic scores. */
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (value, digits=1) => Number.isFinite(value) ? value.toLocaleString(undefined, {maximumFractionDigits:digits}) : 'Not measured';
const percent = value => Number.isFinite(value) ? number(value*100)+'%' : 'Not measured';

export function selectedArchitecture() {
  return document.querySelector('#architecture-select')?.value || 'pointnet2';
}

export async function setupModels() {
  const stylesheet=document.createElement('link');
  stylesheet.rel='stylesheet';stylesheet.href='/assets/features/models.css';document.head.append(stylesheet);
  const rail = document.querySelector('.input-rail .source-tabs');
  const selector = document.createElement('div');
  selector.className = 'model-picker';
  selector.innerHTML = '<label for="architecture-select">Segmentation model</label><select id="architecture-select"><option value="pointnet2">PointNet++ MSG</option><option value="pointnext_s">PointNeXt-S</option></select><p id="architecture-status" role="status">Checking trained models…</p>';
  rail.before(selector);
  selector.querySelector('select').disabled=true;
  const downloadGroup=document.querySelector('#edge-model-downloads');
  if(downloadGroup) downloadGroup.innerHTML='<a class="button download-action model-download disabled" data-edge-download="pointnet2" aria-disabled="true" title="Train and export PointNet++ to enable this download">PointNet++ · Preparing</a><a class="button download-action model-download disabled" data-edge-download="pointnext_s" aria-disabled="true" title="Train and export PointNeXt-S to enable this download">PointNeXt-S · Train first</a>';
  const section = document.createElement('details');
  section.id = 'model-workspace';
  section.className = 'model-workspace panel';
  section.innerHTML = '<summary>Compare trained models and download exports</summary><div class="model-section-heading"><div><h3>Model choices and measured comparison</h3><p>Both architectures use the same scans, four classes and grid policy.</p></div><button id="refresh-models" class="button">Refresh models ↻</button></div><div id="architecture-cards" class="architecture-cards"></div><div id="model-comparison"></div>';
  document.querySelector('#launch .console-layout').after(section);
  const comparisonControls=document.createElement('div');
  comparisonControls.className='model-comparison-controls';
  comparisonControls.innerHTML='<label for="comparison-frames">Scans per model <select id="comparison-frames"><option value="16">16 · quick check</option><option value="32" selected>32 · comparison</option><option value="128">128 · broader coverage</option><option value="512">512 · extended evaluation</option></select></label><button id="compare-models" class="button" disabled>Compare both models</button><span id="comparison-progress" role="status"></span>';
  section.querySelector('#model-comparison').before(comparisonControls);
  let catalog;
  const update = () => {
    if(!catalog)return;
    const model = catalog.models.find(m => m.id === selectedArchitecture());
    document.querySelector('#architecture-status').textContent = model?.ready ? 'New runs use this model. Existing replays keep their original model.' : 'Train the selected model, then refresh to enable processing.';
    document.querySelector('#sample-button').disabled = !model?.ready;
    document.querySelectorAll('[data-model-card]').forEach(card => card.classList.toggle('selected', card.dataset.modelCard === model?.id));
  };
  async function refresh() {
    try {
      const response = await fetch('/api/models');
      if (!response.ok) throw Error('Could not load the model catalog');
      catalog = await response.json();
      document.querySelector('#architecture-select').disabled=false;
      document.querySelector('#compare-models').disabled=!catalog.models.every(m=>m.ready);
      document.querySelector('#architecture-cards').innerHTML = catalog.models.map(m => `
        <article class="architecture-card" data-model-card="${m.id}"><div class="model-title"><h4>${escapeHTML(m.name)}</h4><span class="model-status ${m.ready?'ready':''}">${escapeHTML(m.status)}</span></div>
        <dl><div><dt>Validation block score:</dt><dd>${percent(m.validation_miou)}</dd></div><div><dt>Best checkpoint:</dt><dd>${m.epoch ? 'Epoch '+m.epoch : 'Not trained yet'}</dd></div></dl>
        <div class="model-actions"><button class="button" data-choose-model="${m.id}">Select model</button>${m.download_ready ? `<a class="button model-download" href="${m.download_url}" download>↓ Download model bundle</a>` : `<span class="model-hint">${m.ready?'Export the latest weights to enable download.':'Train and export to enable download.'}</span>`}</div></article>`).join('');
      document.querySelectorAll('[data-choose-model]').forEach(button => button.onclick = () => { document.querySelector('#architecture-select').value=button.dataset.chooseModel; update(); });
      renderComparison(catalog.comparison);
      for(const model of catalog.models) {
        const button=document.querySelector('[data-edge-download="'+model.id+'"]');
        if(!button)continue;
        button.classList.toggle('disabled',!model.download_ready);
        if(model.download_ready) {
          button.href=model.download_url;button.download='PRISM-'+model.id+'-edge.zip';
          button.removeAttribute('aria-disabled');
          button.textContent='↓ '+(model.id==='pointnet2'?'PointNet++':'PointNeXt-S')+' · Download';
          button.title='Download the latest trained '+model.name+' checkpoint';
        } else {
          button.removeAttribute('href');button.removeAttribute('download');button.setAttribute('aria-disabled','true');
          button.textContent=(model.id==='pointnet2'?'PointNet++':'PointNeXt-S')+' · '+(model.ready?'Export needed':'Train first');
          button.title=model.ready?'Export the latest checkpoint to enable this download':'Train '+model.name+' to enable this download';
        }
      }
      update();
    } catch (error) { document.querySelector('#architecture-status').textContent=error.message; }
  }
  document.querySelector('#architecture-select').onchange=update;
  document.querySelector('#refresh-models').onclick=refresh;
  async function pollComparison() {
    try {
      const response=await fetch('/api/models/comparison');
      if(!response.ok) throw Error('Comparison status unavailable');
      const state=await response.json();
      document.querySelector('#comparison-progress').textContent=state.status==='idle'?'':state.status==='failed'?state.error:state.status==='complete'?'Comparison complete':`${state.status==='queued'?'Queued':'Processing'} · ${state.completed} / ${state.total} scans`;
      if(['queued','running'].includes(state.status)) {
        document.querySelector('#compare-models').disabled=true;setTimeout(pollComparison,1500);
      } else if(state.status==='complete') await refresh();
    } catch(error) {document.querySelector('#comparison-progress').textContent=error.message;}
  }
  document.querySelector('#compare-models').onclick=async () => {
    document.querySelector('#compare-models').disabled=true;
    try {
      const response=await fetch('/api/models/comparison?frames='+document.querySelector('#comparison-frames').value,{method:'POST'});
      const state=await response.json();
      if(!response.ok) throw Error(state.detail);
      await pollComparison();
    } catch(error) {document.querySelector('#comparison-progress').textContent=error.message;await refresh();}
  };
  await refresh();
  await pollComparison();
}

function renderComparison(comparison) {
  const target=document.querySelector('#model-comparison');
  if (!comparison) {
    target.innerHTML='<p class="comparison-note">Train both models to unlock a fair comparison on the same scans. Full-scan accuracy and processing speed will appear here. Block validation scores above are not full-scene accuracy.</p>';
    return;
  }
  const rows=comparison.models;
  const metrics=[['Full-scan class overlap (mIoU)',m=>percent(m.semantics.miou)],['Dynamic-object semantic recall · no tracking',m=>percent(m.semantics.recall[3])],['Near map accuracy · 0–10 m',m=>percent(m.by_distance[0].miou)],['Far map accuracy · 25–60 m',m=>percent(m.by_distance[2].miou)],['Typical full-result time · P50',m=>number(m.timing.total_ms.p50)+' ms'],['Slower full-result time · P95',m=>number(m.timing.total_ms.p95)+' ms'],['Grid storage per scan',m=>number(m.mean_grid_mib,2)+' MiB']];
  target.innerHTML=`<h4>Same scans, measured side by side</h4><p class="comparison-note">${comparison.frame_ids.length} sequence 08 validation scans · ${comparison.current?'Both current checkpoints':'Saved checkpoint comparison; rerun to compare the latest weights'}. Processing includes segmentation, both grids, detections and serialization; browser drawing and disk caching are excluded.</p><div class="comparison-scroll"><table><thead><tr><th>What we measured</th>${rows.map(m=>`<th>${m.architecture==='pointnet2'?'PointNet++':'PointNeXt-S'} · epoch ${m.epoch}</th>`).join('')}</tr></thead><tbody>${metrics.map(([title,fn])=>`<tr><td>${title}</td>${rows.map(m=>`<td>${fn(m)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

