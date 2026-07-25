document.addEventListener('DOMContentLoaded', async () => {
  const logoutLink = document.getElementById('logoutLink');
  const mainConcernEl = document.getElementById('mainConcern');
  const generatedNoteEl = document.getElementById('generatedNote');
  const symptomsList = document.getElementById('symptomsList');
  const planList = document.getElementById('planList');

  logoutLink.addEventListener('click', async (event) => {
    event.preventDefault();
    await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
    window.location.href = '/login';
  });

  const patientId = document.body.dataset.patientId;
  if (!patientId) {
    window.location.href = '/login';
    return;
  }

  const response = await fetch('/patient/summary/' + encodeURIComponent(patientId), {
    method: 'GET',
    credentials: 'same-origin',
  });

  if (!response.ok) {
    const error = await response.json();
    mainConcernEl.textContent = 'No clinical summary available yet';
    generatedNoteEl.textContent = error.error || 'Complete the intake and wait for a summary to be generated.';
    return;
  }

  const summary = await response.json();
  const mainConcern = summary.main_concern || 'No clinical summary available yet';
  const generatedAt = summary.generated_at || summary.generatedAt || '';
  const symptoms = Array.isArray(summary.symptoms) ? summary.symptoms : [];
  const plan = Array.isArray(summary.ai_plan)
    ? summary.ai_plan
    : Array.isArray(summary.plan)
      ? summary.plan
      : [];

  mainConcernEl.textContent = mainConcern;
  generatedNoteEl.textContent = generatedAt
    ? `AI-organized summary generated ${generatedAt} — reviewed by Dr. Sarah Khan before any clinical decision.`
    : 'AI-organized summary — reviewed by Dr. Sarah Khan before any clinical decision.';

  symptomsList.innerHTML = '';
  if (symptoms.length === 0) {
    symptomsList.innerHTML = `
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding-bottom:12px;border-bottom:1px solid var(--border)">
        <div>
          <div style="font-size:14px;font-weight:700;color:var(--text-primary)">No symptom details yet</div>
          <div style="font-size:13px;color:var(--text-secondary);margin-top:2px">Complete intake to populate symptom details.</div>
        </div>
      </div>
    `;
  } else {
    symptoms.forEach((item) => {
      const label = item.name || item.label || 'Symptom';
      const detailParts = [];
      if (item.duration) detailParts.push(item.duration);
      if (item.severity_reported) detailParts.push(`Severity reported: ${item.severity_reported}`);
      if (item.severity_inferred) detailParts.push(`Severity inferred: ${item.severity_inferred}`);
      if (item.location) detailParts.push(`Location: ${item.location}`);
      if (item.onset_description) detailParts.push(item.onset_description);
      if (item.detail) detailParts.push(item.detail);
      const detail = detailParts.length > 0 ? detailParts.join(' · ') : 'No additional detail available.';
      const flagged = item.flagged === true;
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.alignItems = 'flex-start';
      row.style.justifyContent = 'space-between';
      row.style.gap = '12px';
      row.style.paddingBottom = '12px';
      row.style.borderBottom = '1px solid var(--border)';

      const textBlock = document.createElement('div');
      const title = document.createElement('div');
      title.style.fontSize = '14px';
      title.style.fontWeight = '700';
      title.style.color = 'var(--text-primary)';
      title.textContent = label;
      const detailEl = document.createElement('div');
      detailEl.style.fontSize = '13px';
      detailEl.style.color = 'var(--text-secondary)';
      detailEl.style.marginTop = '2px';
      detailEl.textContent = detail;
      textBlock.appendChild(title);
      textBlock.appendChild(detailEl);
      row.appendChild(textBlock);

      if (flagged) {
        const flag = document.createElement('span');
        flag.style.background = 'var(--danger-soft)';
        flag.style.color = 'var(--danger)';
        flag.style.fontSize = '11px';
        flag.style.fontWeight = '700';
        flag.style.padding = '4px 10px';
        flag.style.borderRadius = '999px';
        flag.style.whiteSpace = 'nowrap';
        flag.textContent = 'FLAGGED';
        row.appendChild(flag);
      }

      symptomsList.appendChild(row);
    });
  }

  planList.innerHTML = '';
  if (plan.length === 0) {
    planList.innerHTML = '<div style="font-size:14px;color:var(--text-secondary)">No AI plan available yet.</div>';
  } else {
    plan.forEach((item) => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.gap = '10px';
      row.style.alignItems = 'flex-start';
      row.style.marginBottom = '10px';
      row.style.fontSize = '14px';
      row.style.color = 'var(--text-primary)';
      row.style.lineHeight = '1.5';

      const bullet = document.createElement('span');
      bullet.style.width = '6px';
      bullet.style.height = '6px';
      bullet.style.borderRadius = '50%';
      bullet.style.background = 'var(--accent)';
      bullet.style.marginTop = '8px';
      bullet.style.flexShrink = '0';

      const text = document.createElement('span');
      text.textContent = item;

      row.appendChild(bullet);
      row.appendChild(text);
      planList.appendChild(row);
    });
  }
});
