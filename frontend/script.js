document.addEventListener("DOMContentLoaded", () => {

const API_URL = 'http://127.0.0.1:8000/analyze/';
const uploadZone = document.getElementById('uploadZone');
const resumeFile = document.getElementById('resumeFile');
const fileNameEl = document.getElementById('fileName');

resumeFile.addEventListener('change', () => {
  if (resumeFile.files[0]) showFileName(resumeFile.files[0].name);
});

uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));

document.getElementById("analyzeBtn").addEventListener("click", analyze);

uploadZone.addEventListener('drop', e => {
  e.preventDefault(); uploadZone.classList.remove('dragover');
  const f = e.dataTransfer.files[0];
  if (f && f.type === 'application/pdf') {
    const dt = new DataTransfer(); dt.items.add(f); resumeFile.files = dt.files;
    showFileName(f.name);
  }
});

function showFileName(name) {
  fileNameEl.textContent = '✓ ' + name;
  fileNameEl.style.display = 'block';
}

function verdict(s) {
  if (s >= 85) return { text:'Excellent Match', sub:'Your resume is a strong fit for this role.',           color:'#16a34a', tint:'tint-green' };
  if (s >= 70) return { text:'Good Match',       sub:'A few tweaks could make your profile stand out.',     color:'#2563eb', tint:'tint-green' };
  if (s >= 50) return { text:'Moderate Match',   sub:'Several key skills are missing or underdeveloped.',   color:'#d97706', tint:'tint-amber' };
  if (s >= 40) return { text:'Weak Match',        sub:'Significant gaps between your resume and the role.', color:'#ea580c', tint:'tint-amber' };
  return               { text:'Poor Match',       sub:'Your resume needs major work for this position.',    color:'#dc2626', tint:'tint-red'   };
}

function renderTags(id, items, emptyMsg) {
  const el = document.getElementById(id);
  el.innerHTML = '';
  if (!items?.length) { el.innerHTML = `<span class="empty-note">${emptyMsg}</span>`; return; }
  items.forEach(s => {
    const t = document.createElement('span'); t.className = 'tag'; t.textContent = s; el.appendChild(t);
  });
}

function renderList(id, items, emptyMsg) {
  const el = document.getElementById(id);
  el.innerHTML = '';
  if (!items?.length) { el.innerHTML = `<li style="color:var(--light);font-style:italic">${emptyMsg}</li>`; return; }
  items.forEach((item, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<div class="item-num">${i+1}</div><div>${item}</div>`;
    el.appendChild(li);
  });
}

function renderResults(data) {
  const score = Math.round(data.score ?? 0);
  const v = verdict(score);

  document.getElementById('scoreNum').textContent     = score;
  document.getElementById('scoreVerdict').textContent = v.text;
  document.getElementById('scoreVerdict').style.color = v.color;
  document.getElementById('scoreSub').textContent     = v.sub;
  const ring = document.getElementById('ringFg');
  ring.style.stroke = v.color;
  setTimeout(() => { ring.style.strokeDashoffset = 390 * (1 - score / 100); }, 80);

  const hero = document.querySelector('.score-hero');
  hero.classList.remove('tint-green', 'tint-amber', 'tint-red');
  hero.classList.add(v.tint);

  document.getElementById('matchedCount').textContent = data.matched_skills?.length ?? 0;
  document.getElementById('missingCount').textContent  = data.missing_skills?.length  ?? 0;

  renderTags('matchedSkills', data.matched_skills, 'No matched skills found');
  renderTags('missingSkills', data.missing_skills, 'No missing skills — great!');
  renderList('feedbackList',     data.feedback,         'No feedback provided.');
  renderList('improvementsList', data.top_improvements, 'No improvements listed.');

  document.getElementById('emptyState').style.display = 'none';
  const results = document.getElementById('results');
  results.classList.add('on');
  setTimeout(() => results.scrollIntoView({ behavior:'smooth', block:'start' }), 100);
}

async function analyze() {
  const file    = resumeFile.files[0];
  const jobDesc = document.getElementById('jobDesc').value.trim();
  const btn     = document.getElementById('analyzeBtn');
  const loader  = document.getElementById('loader');
  const errBox  = document.getElementById('errorBox');
  const results = document.getElementById('results');

  errBox.classList.remove('on');
  results.classList.remove('on');

  if (!file)    { showError('Please upload a PDF resume first.'); return; }
  if (!jobDesc) { showError('Please paste a job description.'); return; }

  btn.disabled = true;
  btn.innerHTML = '<div class="spin" style="border-top-color:#fff"></div> Analyzing…';
  loader.classList.add('on');

  try {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('job_desc', jobDesc);

    const res = await fetch(API_URL, { method:'POST', body:fd });

    if (!res.ok) {
      let msg = `Server error ${res.status}: ${res.statusText}`;
      try {
        const e = await res.json();
        if (e.error) msg = e.error;
        else if (e.detail) msg = e.detail;
      } catch(_) {}
      throw new Error(msg);
    }

    renderResults(await res.json());

  } catch (err) {
    showError(
      err.name === 'TypeError'
        ? `Could not connect to ${API_URL}. Make sure your FastAPI backend is running.`
        : 'Failed to analyze resume. ' + (err.message || 'Try again.')
    );
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡</span> Analyze Resume';
    loader.classList.remove('on');
  }
}

function showError(msg) {
  const el = document.getElementById('errorBox');
  el.textContent = '⚠ ' + msg;
  el.classList.add('on');
}
})
