/* Build one persistent dashboard. Cards stay visible together; no page-jump navigation. */
export function arrangeWorkspace({ benchViewer, launchViewer }) {
  const $ = selector => document.querySelector(selector);
  const main = $('main');
  const benchmark = $('#benchmark');
  const launch = $('#launch');
  const readme = $('#readme');
  const evidence = $('#benchmark-evidence-drawer');
  const heading = benchmark.querySelector('.workspace-heading h1');
  if (heading) heading.textContent = 'Adaptive LiDAR mapping';

  if (!benchmark.querySelector('.project-overview-card')) {
    const project = document.createElement('article');
    project.className = 'project-overview-card panel';
    project.innerHTML = '<div><span class="eyebrow">PROJECT OVERVIEW</span><h2>Fine detail near the vehicle. Larger cells farther away.</h2><p>PRISM labels each scan and maps height and class. It keeps smaller cells nearby and uses larger cells at a distance.</p></div><div class="overview-facts"><span><b>Input:</b> SemanticKITTI scans</span><span><b>Models:</b> PointNet++ and PointNeXt-S</span><span><b>Map:</b> Height and class</span><span><b>Test:</b> Sequence 08</span></div>';
    $('#judge-metrics').after(project);
  }

  const dashboard = document.createElement('div');
  dashboard.id = 'prism-dashboard';
  dashboard.className = 'dashboard-grid';
  main.prepend(dashboard);

  const mapCard = document.createElement('section');
  mapCard.className = 'dashboard-card dashboard-map-card';
  mapCard.setAttribute('aria-label', 'Synchronized adaptive grid comparison');
  dashboard.append(mapCard);
  [benchmark.querySelector('.workspace-heading'), benchmark.querySelector('.modebar'),
   benchmark.querySelector('.judge-navigation'), $('#judge-metrics'), $('#compute-evidence'),
   $('.project-overview-card'), benchmark.querySelector('.lab-toolbar'),
   $('#benchmark-viewer')].filter(Boolean).forEach(node => mapCard.append(node));

  // The two trained architectures remain immediately beside the map comparison.
  const modelCard = document.createElement('section');
  modelCard.className = 'dashboard-card dashboard-model-card';
  modelCard.setAttribute('aria-label', 'Trained model comparison and downloads');
  dashboard.append(modelCard);
  const models = launch.querySelector('.model-workspace');
  if (models) {
    models.id = 'model-workspace';
    models.open = true;
    const summary = models.querySelector('summary');
    if (summary) summary.textContent = 'Compare trained models';
    const title = models.querySelector('.model-section-heading h3');
    if (title) title.textContent = 'Two trained architectures. One fair comparison.';
    modelCard.append(models);
  }
  const downloads = $('#edge-model-downloads');
  if (downloads) modelCard.prepend(downloads);
  const exportNote = readme.querySelector('.export-scope');
  if (exportNote) modelCard.append(exportNote);
  const training = readme.querySelector('.readme-grid');
  if (training) {
    const trainingCard = document.createElement('section');
    trainingCard.className = 'training-card panel';
    trainingCard.innerHTML = '<div class="eyebrow">TRAINING EVIDENCE</div><h2>Validation learning curve</h2>';
    trainingCard.append(training);
    modelCard.append(trainingCard);
  }

  const processCard = document.createElement('section');
  processCard.className = 'dashboard-card dashboard-process-card';
  processCard.setAttribute('aria-label', 'Local point cloud processing');
  dashboard.append(processCard);
  [launch.querySelector('.workspace-heading'), launch.querySelector('.console-layout'),
   launch.querySelector('.detection-strip')].filter(Boolean).forEach(node => processCard.append(node));

  if (evidence) {
    evidence.open = true;
    evidence.classList.add('dashboard-evidence-card');
    dashboard.append(evidence);
  }

  // Lightweight floating navigation keeps the long, single-page demo easy to
  // scan without changing the dashboard's card layout or interrupting scrolling.
  const scrollGuide = document.createElement('div');
  scrollGuide.className = 'scroll-guide';
  scrollGuide.innerHTML = `
    <div class="scroll-progress" role="progressbar" aria-label="Page progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span></span></div>
    <nav class="section-nav" aria-label="Jump to dashboard section">
      <span class="section-nav-current" aria-live="polite">01 · Compare</span>
      <a href="#dashboard-compare" data-section="0" aria-label="Go to map comparison">Compare</a>
      <a href="#dashboard-models" data-section="1" aria-label="Go to trained model comparison">Models</a>
      <a href="#dashboard-process" data-section="2" aria-label="Go to point cloud processing">Process</a>
      <a href="#benchmark-evidence-drawer" data-section="3" aria-label="Go to detailed evidence">Evidence</a>
      <button type="button" class="section-top" aria-label="Back to top" title="Back to top">↑</button>
    </nav>`;
  mapCard.id = 'dashboard-compare';
  modelCard.id = 'dashboard-models';
  processCard.id = 'dashboard-process';
  document.body.append(scrollGuide);

  const sectionLinks = [...scrollGuide.querySelectorAll('[data-section]')];
  const sections = [mapCard, modelCard, processCard, evidence].filter(Boolean);
  const progress = scrollGuide.querySelector('.scroll-progress');
  const currentLabel = scrollGuide.querySelector('.section-nav-current');
  let scrollTick = 0;
  const updateScrollGuide = () => {
    scrollTick = 0;
    const root = document.documentElement;
    const maxScroll = Math.max(1, root.scrollHeight - innerHeight);
    const percent = Math.round((root.scrollTop / maxScroll) * 100);
    progress.style.setProperty('--scroll-progress', `${percent}%`);
    progress.setAttribute('aria-valuenow', String(percent));

    const probe = innerHeight * 0.34;
    let active = 0;
    sections.forEach((section, index) => {
      if (section.getBoundingClientRect().top <= probe) active = index;
    });
    if (root.scrollTop + innerHeight >= root.scrollHeight - 8) active = sections.length - 1;
    sectionLinks.forEach((link, index) => {
      if (index === active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    currentLabel.textContent = `${String(active + 1).padStart(2, '0')} · ${['Compare', 'Models', 'Process', 'Evidence'][active]}`;
  };
  const requestScrollUpdate = () => {
    if (!scrollTick) scrollTick = requestAnimationFrame(updateScrollGuide);
  };
  addEventListener('scroll', requestScrollUpdate, { passive: true });
  addEventListener('resize', requestScrollUpdate, { passive: true });
  requestScrollUpdate();
  sectionLinks.forEach((link) => link.addEventListener('click', (event) => {
    event.preventDefault();
    const section = sections[Number(link.dataset.section)];
    section?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }));
  scrollGuide.querySelector('.section-top').addEventListener('click', () => {
    mapCard.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  });
  const status = $('#benchmark-status');
  if (status && evidence) evidence.append(status);
  const compute = $('#compute-evidence');
  if (compute && evidence && !mapCard.contains(compute)) mapCard.append(compute);

  // Keep the legacy section IDs mounted for existing API/render code, without
  // retaining empty route-sized shells in the visible layout.
  [benchmark, launch, readme].forEach(section => {
    section.classList.add('dashboard-source');
    section.setAttribute('aria-hidden', 'true');
  });
  window.addEventListener('prism:job-started', () => {});
  window.addEventListener('prism:route-changed', () => {
    requestAnimationFrame(() => { benchViewer.draw(); launchViewer.draw(); });
  });
  requestAnimationFrame(() => { benchViewer.draw(); launchViewer.draw(); });
}
