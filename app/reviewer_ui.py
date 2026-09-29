"""Dependency-free reviewer console served by FastAPI.

The UI inserts document data only through DOM ``textContent``/text nodes. The
source text is untrusted input, so it must never be interpolated as HTML.
"""

REVIEWER_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DocuGuard · Reviewer Console</title>
  <style>
    :root { color-scheme:dark; --bg:#10151e; --panel:#19212e; --line:#314054; --text:#edf3fc; --muted:#9eabc0; --blue:#80b7ff; --red:#ff9696; --amber:#ffd17a; --green:#9ce3b1; }
    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text); font:14px/1.45 ui-sans-serif,system-ui,-apple-system,sans-serif; }
    header { padding:20px 28px; border-bottom:1px solid var(--line); display:flex; align-items:center; justify-content:space-between; gap:18px; } h1,h2,h3,p { margin:0; } h1 { font-size:20px; } h2 { font-size:16px; } h3 { font-size:14px; } .subtle { color:var(--muted); font-size:13px; }
    main { display:grid; grid-template-columns:270px minmax(0,1fr); min-height:calc(100vh - 69px); } aside { border-right:1px solid var(--line); padding:18px; } #case { padding:24px; max-width:1340px; width:100%; } .stack { display:grid; gap:10px; } .grid { display:grid; gap:16px; } .two { grid-template-columns:repeat(2,minmax(0,1fr)); } .row { display:flex; align-items:center; gap:8px; flex-wrap:wrap; } .between { justify-content:space-between; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; } .card > h2 { margin-bottom:12px; } .queue-item,button { font:inherit; } .queue-item { display:block; width:100%; text-align:left; padding:12px; margin:8px 0; color:var(--text); background:transparent; border:1px solid var(--line); border-radius:8px; cursor:pointer; } .queue-item:hover,.queue-item.selected { border-color:var(--blue); background:#1d2a3c; }
    .pill { border-radius:999px; padding:3px 8px; border:1px solid var(--line); font-size:12px; } .critical { color:var(--red); border-color:#844; } .advisory { color:var(--amber); border-color:#886c35; } .ready_for_review { color:var(--amber); } .approved { color:var(--green); } .rejected { color:var(--red); }
    .finding { border-left:3px solid var(--amber); padding:10px 12px; background:#221e16; text-align:left; color:var(--text); } .finding.critical { border-left-color:var(--red); background:#28191d; } button.finding { width:100%; border-top:0; border-right:0; border-bottom:0; border-radius:0; cursor:pointer; } button.finding:hover { filter:brightness(1.13); }
    .workspace { grid-template-columns:minmax(280px,.9fr) minmax(0,1.3fr); } .document-list { display:grid; gap:12px; } .document-section { border-top:1px solid var(--line); padding-top:12px; } .document-section:first-of-type { border-top:0; padding-top:0; } .field-row { display:grid; grid-template-columns:minmax(92px,.75fr) minmax(0,1fr) auto; align-items:center; gap:8px; width:100%; border:0; border-radius:6px; padding:8px; background:transparent; color:var(--text); text-align:left; cursor:pointer; } .field-row:hover,.field-row:focus { background:#243247; outline:none; } .field-row span { color:var(--muted); font-size:12px; } .field-row strong { overflow-wrap:anywhere; font-weight:500; } .confidence-low { color:var(--amber) !important; } .confidence-high { color:var(--green) !important; }
    .source-meta { display:grid; gap:2px; margin-bottom:10px; } pre { white-space:pre-wrap; overflow-wrap:anywhere; margin:0; min-height:330px; max-height:560px; overflow:auto; padding:14px; background:#0d121a; border:1px solid var(--line); border-radius:7px; color:#d8e5f8; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; } mark { background:#6d5120; color:var(--text); border-radius:2px; padding:1px 0; }
    input,select,textarea { width:100%; padding:8px; background:#0d121a; color:var(--text); border:1px solid var(--line); border-radius:6px; } textarea { min-height:72px; resize:vertical; } label { display:grid; gap:4px; color:var(--muted); font-size:12px; } form { display:grid; gap:10px; } button { background:#2869b7; color:white; padding:8px 11px; border:0; border-radius:6px; cursor:pointer; } button:hover { background:#367acd; } #notice { min-height:20px; color:var(--amber); } .empty { color:var(--muted); padding:36px 0; }
    @media (max-width:900px) { main { grid-template-columns:1fr; } aside { border-right:0; border-bottom:1px solid var(--line); } .workspace,.two { grid-template-columns:1fr; } pre { min-height:240px; } } @media (max-width:560px) { header,#case { padding-left:16px; padding-right:16px; } .field-row { grid-template-columns:1fr auto; } .field-row strong { grid-column:1 / -1; } }
  </style>
</head>
<body>
  <header><div><h1>DocuGuard · Reviewer Console</h1><p class="subtle">Human decisions are explicit, reasoned, and audited.</p></div><a class="subtle" href="/docs">API docs</a></header>
  <main><aside><div class="row between"><h2>Review queue</h2><button id="refresh" type="button">Refresh</button></div><div id="queue" class="stack"></div></aside><section id="case"><p class="empty">Loading review queue…</p></section></main>
  <script>
    const queueElement = document.querySelector('#queue');
    const caseElement = document.querySelector('#case');
    const params = new URLSearchParams(window.location.search);
    const REVIEW_FIELDS = [['supplier_name', 'Supplier'], ['document_number', 'Document number'], ['document_date', 'Date'], ['currency', 'Currency'], ['total', 'Total']];
    let selectedId = params.get('case');
    let reviewerToken = sessionStorage.getItem('docuguard-review-token') || '';

    function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
    function tag(text, className) { return node('span', text, `pill ${className || ''}`); }
    function format(value) { return value === null || value === undefined || value === '' ? '—' : String(value); }
    function clear(element) { element.replaceChildren(); }
    async function request(url, options) { const response = await fetch(url, options); if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `Request failed (${response.status})`); } return response.json(); }
    function reviewerHeaders() { const headers = {'content-type':'application/json'}; if (reviewerToken) headers['X-DocuGuard-Review-Token'] = reviewerToken; return headers; }
    function fieldForDiscrepancy(type, message) { if (type.includes('total')) return 'total'; if (type.includes('supplier')) return 'supplier_name'; if (type.includes('currency')) return 'currency'; const match = message?.match(/Field '([a-z_]+)'|Required field '([a-z_]+)'/); return match?.[1] || match?.[2] || null; }

    async function loadQueue() {
      const bundles = await request('/bundles?status=ready_for_review'); clear(queueElement);
      if (!bundles.length) { queueElement.append(node('p', 'No cases waiting for review.', 'subtle')); clear(caseElement); caseElement.append(node('p', 'The queue is empty. Seed the demo or upload a case.', 'empty')); return; }
      if (!selectedId || !bundles.some(bundle => bundle.id === selectedId)) selectedId = bundles[0].id;
      bundles.forEach(bundle => { const button = node('button', undefined, `queue-item ${bundle.id === selectedId ? 'selected' : ''}`); button.type = 'button'; button.append(node('strong', bundle.tenant_id), node('div', bundle.id.slice(0, 8), 'subtle')); button.onclick = () => { selectedId = bundle.id; history.replaceState(null, '', `/reviewer?case=${bundle.id}`); loadQueue().then(loadCase); }; queueElement.append(button); });
    }

    function appendHighlightedText(target, text, evidence) {
      const source = text || 'No extracted text is available.'; const query = evidence || ''; const index = query ? source.toLocaleLowerCase().indexOf(query.toLocaleLowerCase()) : -1;
      if (index < 0) { target.textContent = source; return; }
      target.append(document.createTextNode(source.slice(0, index)), node('mark', source.slice(index, index + query.length)), document.createTextNode(source.slice(index + query.length)));
    }

    function evidenceWorkspace(data) {
      const workspace = node('section', undefined, 'grid workspace'); const fieldsPanel = node('section', undefined, 'card'); fieldsPanel.append(node('h2', 'Evidence workspace'), node('p', 'Select an extracted field or finding to focus its supporting text.', 'subtle'));
      const documentList = node('div', undefined, 'document-list'); fieldsPanel.append(documentList);
      const sourcePanel = node('section', undefined, 'card'); sourcePanel.append(node('h2', 'Source text')); const sourceMeta = node('div', undefined, 'source-meta'); const sourceText = node('pre'); sourcePanel.append(sourceMeta, sourceText);

      function showEvidence(documentId, fieldName) {
        const document = data.documents.find(item => item.id === documentId) || data.documents[0]; const fields = document.fields || {}; const evidence = fieldName ? fields[`${fieldName}_evidence`] : null;
        clear(sourceMeta); sourceMeta.append(node('strong', document.original_filename), node('span', fieldName ? `${fieldName.replaceAll('_', ' ')} evidence: ${format(evidence)}` : 'Document source text', 'subtle'));
        clear(sourceText); appendHighlightedText(sourceText, document.extraction?.text_content, evidence);
      }

      data.documents.forEach(document => {
        const section = node('article', undefined, 'document-section'); const heading = node('div', undefined, 'row between'); const label = node('div'); label.append(node('h3', document.original_filename), node('p', `${document.document_type} · ${document.processing_status}`, 'subtle')); heading.append(label, tag(document.extraction?.quality_status || 'not extracted')); section.append(heading);
        if (document.fields) REVIEW_FIELDS.forEach(([fieldName, labelText]) => { const value = document.fields[`${fieldName}_value`]; const confidence = document.fields[`${fieldName}_confidence`]; const button = node('button', undefined, 'field-row'); button.type='button'; button.append(node('span', labelText), node('strong', format(value)), node('span', `${Math.round((confidence || 0) * 100)}%`, confidence < .7 ? 'confidence-low' : 'confidence-high')); button.onclick = () => showEvidence(document.id, fieldName); section.append(button); });
        else section.append(node('p', 'No structured fields were extracted.', 'subtle'));
        documentList.append(section);
      });

      const priorityFinding = data.discrepancies.find(item => item.severity === 'critical') || data.discrepancies[0];
      showEvidence(priorityFinding?.document_ids?.[0] || data.documents[0]?.id, fieldForDiscrepancy(priorityFinding?.discrepancy_type || '', priorityFinding?.message));
      workspace.append(fieldsPanel, sourcePanel); return { workspace, showEvidence };
    }

    function findingsPanel(data, showEvidence) { const findings = node('section', undefined, 'card stack'); findings.append(node('h2', `Findings (${data.discrepancies.length})`)); if (!data.discrepancies.length) findings.append(node('p', 'No deterministic discrepancies found.', 'subtle')); data.discrepancies.forEach(item => { const finding = node('button', undefined, `finding ${item.severity}`); finding.type='button'; finding.append(node('div', undefined, 'row'), node('strong', item.discrepancy_type), tag(item.severity, item.severity), node('p', item.message), node('p', 'Open evidence', 'subtle')); finding.onclick = () => showEvidence(item.document_ids[0], fieldForDiscrepancy(item.discrepancy_type, item.message)); findings.append(finding); }); return findings; }
    function renderCase(data) { clear(caseElement); const title = node('div', undefined, 'row between'); const left = node('div'); left.append(node('h2', `Case · ${data.bundle.tenant_id}`), node('p', data.bundle.id, 'subtle')); title.append(left, tag(data.bundle.status, data.bundle.status)); caseElement.append(title); const notice = node('p', '', 'subtle'); notice.id = 'notice'; caseElement.append(notice, reviewerAccessPanel(notice)); const evidence = evidenceWorkspace(data); caseElement.append(findingsPanel(data, evidence.showEvidence), evidence.workspace); const actions = node('div', undefined, 'grid two'); actions.append(decisionPanel(data, notice), correctionPanel(data, notice)); caseElement.append(actions, auditPanel(data)); }
    function decisionPanel(data, notice) { const panel = node('section', undefined, 'card'); panel.append(node('h2', 'Record case decision')); const form = document.createElement('form'); form.append(formField('Action', selectField('action', [['approved','Approve'], ['rejected','Reject'], ['needs_info','Needs information']])), formField('Actor', inputField('actor', 'reviewer@example.com')), formField('Reason', textAreaField('reason', 'Explain the review decision.'))); const button = node('button', 'Record decision'); button.type='submit'; form.append(button); form.onsubmit = async event => { event.preventDefault(); try { await request(`/bundles/${data.bundle.id}/decision`, {method:'POST', headers:reviewerHeaders(), body:JSON.stringify(Object.fromEntries(new FormData(form)))}); notice.textContent='Decision recorded in the audit trail.'; await loadQueue(); await loadCase(); } catch (error) { notice.textContent=error.message; } }; panel.append(form); return panel; }
    function auditPanel(data) { const audit = node('section', undefined, 'card stack'); audit.append(node('h2', `Audit history (${data.audit_events.length})`)); if (!data.audit_events.length) audit.append(node('p', 'No human action has been recorded yet.', 'subtle')); data.audit_events.forEach(event => { const entry=node('div', undefined, 'finding'); entry.append(node('strong', `${event.event_type}: ${event.action}`), node('p', `${event.actor} · ${new Date(event.created_at).toLocaleString()}`, 'subtle'), node('p', event.reason || 'No reason recorded.')); audit.append(entry); }); return audit; }
    function formField(labelText, control) { const label=node('label', labelText); label.append(control); return label; }
    function inputField(name, value) { const input=document.createElement('input'); input.name=name; input.value=value; input.required=true; return input; }
    function textAreaField(name, value) { const area=document.createElement('textarea'); area.name=name; area.value=value; area.required=true; return area; }
    function selectField(name, choices) { const select=document.createElement('select'); select.name=name; choices.forEach(([value, label])=>{ const option=node('option', label); option.value=value; select.append(option); }); return select; }
    function reviewerAccessPanel(notice) { const panel=node('section', undefined, 'card'); panel.append(node('h2', 'Reviewer access'), node('p', 'Viewing this synthetic case is open. Enter the access code you received to record a decision or correction.', 'subtle')); const form=document.createElement('form'); const input=inputField('reviewer_token', reviewerToken); input.type='password'; input.autocomplete='off'; input.placeholder='Access code'; input.required=false; form.append(formField('Access code', input)); const button=node('button','Save for this browser session'); button.type='submit'; form.append(button); form.onsubmit=event=>{ event.preventDefault(); reviewerToken=input.value.trim(); if (reviewerToken) sessionStorage.setItem('docuguard-review-token', reviewerToken); else sessionStorage.removeItem('docuguard-review-token'); notice.textContent=reviewerToken ? 'Reviewer access code saved for this browser session.' : 'Reviewer access code cleared.'; }; return panel; }
    function correctionPanel(data, notice) { const panel=node('section', undefined, 'card'); panel.append(node('h2', 'Record field correction')); const form=document.createElement('form'); const documentSelect=selectField('document_id', data.documents.map(document=>[document.id, document.original_filename])); form.append(formField('Document', documentSelect), formField('Field', selectField('field_name', REVIEW_FIELDS)), formField('Action', selectField('action', [['corrected','Corrected'], ['kept','Kept as extracted'], ['marked_unavailable','Marked unavailable']])), formField('New value (for corrected)', inputField('new_value', '')), formField('Actor', inputField('actor', 'reviewer@example.com')), formField('Reason', textAreaField('reason', 'Explain the correction.'))); const button=node('button','Record correction'); button.type='submit'; form.append(button); form.onsubmit=async event=>{ event.preventDefault(); try { const values=Object.fromEntries(new FormData(form)); const documentId=values.document_id; delete values.document_id; if (values.action !== 'corrected') delete values.new_value; await request(`/bundles/${data.bundle.id}/documents/${documentId}/corrections`, {method:'POST',headers:reviewerHeaders(),body:JSON.stringify(values)}); notice.textContent='Correction recorded; original extraction remains unchanged.'; await loadCase(); } catch(error) { notice.textContent=error.message; } }; panel.append(form); return panel; }
    async function loadCase() { if (!selectedId) return; try { renderCase(await request(`/bundles/${selectedId}/review`)); } catch(error) { clear(caseElement); caseElement.append(node('p', error.message, 'empty')); } }
    document.querySelector('#refresh').onclick = () => loadQueue().then(loadCase);
    loadQueue().then(loadCase).catch(error => { clear(caseElement); caseElement.append(node('p', error.message, 'empty')); });
  </script>
</body></html>"""
