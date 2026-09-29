"""Small, dependency-free reviewer console served by FastAPI.

The UI inserts all API data with ``textContent``. Document text is untrusted
input, so rendering it through ``innerHTML`` would turn a reviewer tool into a
stored-XSS sink.
"""

REVIEWER_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DocuGuard · Reviewer Console</title>
  <style>
    :root { color-scheme: dark; --bg:#10151e; --panel:#19212e; --line:#314054; --text:#edf3fc; --muted:#9eabc0; --blue:#80b7ff; --red:#ff9696; --amber:#ffd17a; --green:#9ce3b1; }
    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text); font:14px/1.45 ui-sans-serif,system-ui,-apple-system,sans-serif; }
    header { padding:20px 28px; border-bottom:1px solid var(--line); display:flex; align-items:center; justify-content:space-between; } h1,h2,h3,p { margin:0; } h1 { font-size:20px; } h2 { font-size:16px; } h3 { font-size:14px; } .subtle { color:var(--muted); font-size:13px; }
    main { display:grid; grid-template-columns:270px minmax(0,1fr); min-height:calc(100vh - 69px); } aside { border-right:1px solid var(--line); padding:18px; } #case { padding:24px; max-width:1280px; } .queue-item, button { font:inherit; } .queue-item { display:block; width:100%; text-align:left; padding:12px; margin:8px 0; color:var(--text); background:transparent; border:1px solid var(--line); border-radius:8px; cursor:pointer; } .queue-item:hover,.queue-item.selected { border-color:var(--blue); background:#1d2a3c; }
    .grid { display:grid; gap:16px; } .two { grid-template-columns:repeat(2,minmax(0,1fr)); } .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; } .card > h2 { margin-bottom:12px; } .stack { display:grid; gap:10px; } .row { display:flex; align-items:center; gap:8px; flex-wrap:wrap; } .between { justify-content:space-between; }
    .pill { border-radius:999px; padding:3px 8px; border:1px solid var(--line); font-size:12px; } .critical { color:var(--red); border-color:#844; } .advisory { color:var(--amber); border-color:#886c35; } .ready_for_review { color:var(--amber); } .approved { color:var(--green); } .rejected { color:var(--red); }
    .finding { border-left:3px solid var(--amber); padding:9px 11px; background:#221e16; } .finding.critical { border-left-color:var(--red); background:#28191d; } pre { white-space:pre-wrap; overflow-wrap:anywhere; margin:8px 0 0; padding:12px; background:#0d121a; border:1px solid var(--line); border-radius:7px; color:#d8e5f8; font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; }
    table { width:100%; border-collapse:collapse; } td { padding:7px 0; border-top:1px solid var(--line); vertical-align:top; } td:first-child { color:var(--muted); width:38%; } input,select,textarea { width:100%; padding:8px; background:#0d121a; color:var(--text); border:1px solid var(--line); border-radius:6px; } textarea { min-height:72px; resize:vertical; } label { display:grid; gap:4px; color:var(--muted); font-size:12px; } form { display:grid; gap:10px; } button { background:#2869b7; color:white; padding:8px 11px; border:0; border-radius:6px; cursor:pointer; } button:hover { background:#367acd; } #notice { min-height:20px; color:var(--amber); } .empty { color:var(--muted); padding:36px 0; } @media (max-width:800px) { main { grid-template-columns:1fr; } aside { border-right:0; border-bottom:1px solid var(--line); } .two { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header><div><h1>DocuGuard · Reviewer Console</h1><p class="subtle">Human decisions are explicit, reasoned, and audited.</p></div><a class="subtle" href="/docs">API docs</a></header>
  <main><aside><div class="row between"><h2>Review queue</h2><button id="refresh" type="button">Refresh</button></div><div id="queue" class="stack"></div></aside><section id="case"><p class="empty">Loading review queue…</p></section></main>
  <script>
    const queueElement = document.querySelector('#queue');
    const caseElement = document.querySelector('#case');
    const params = new URLSearchParams(window.location.search);
    let selectedId = params.get('case');
    let currentCase = null;

    function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
    function tag(text, className) { return node('span', text, `pill ${className || ''}`); }
    function format(value) { return value === null || value === undefined || value === '' ? '—' : String(value); }
    function clear(element) { element.replaceChildren(); }
    async function request(url, options) { const response = await fetch(url, options); if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `Request failed (${response.status})`); } return response.json(); }

    async function loadQueue() {
      const bundles = await request('/bundles?status=ready_for_review');
      clear(queueElement);
      if (!bundles.length) { queueElement.append(node('p', 'No cases waiting for review.', 'subtle')); clear(caseElement); caseElement.append(node('p', 'The queue is empty. Seed the demo or upload a case.', 'empty')); return; }
      if (!selectedId || !bundles.some(bundle => bundle.id === selectedId)) selectedId = bundles[0].id;
      bundles.forEach(bundle => { const button = node('button', undefined, `queue-item ${bundle.id === selectedId ? 'selected' : ''}`); button.type = 'button'; button.append(node('strong', bundle.tenant_id)); button.append(node('div', bundle.id.slice(0, 8), 'subtle')); button.onclick = () => { selectedId = bundle.id; history.replaceState(null, '', `/reviewer?case=${bundle.id}`); loadQueue().then(loadCase); }; queueElement.append(button); });
    }

    function fieldTable(fields) {
      const table = node('table');
      [['Document type', fields.document_type], ['Supplier', fields.supplier_name_value], ['Supplier confidence', fields.supplier_name_confidence], ['Document number', fields.document_number_value], ['Date', fields.document_date_value], ['Currency', fields.currency_value], ['Total', fields.total_value], ['Total confidence', fields.total_confidence]].forEach(([name, value]) => { const row = node('tr'); row.append(node('td', name), node('td', format(value))); table.append(row); });
      return table;
    }

    function renderCase(data) {
      currentCase = data; clear(caseElement);
      const title = node('div', undefined, 'row between'); const left = node('div'); left.append(node('h2', `Case · ${data.bundle.tenant_id}`), node('p', data.bundle.id, 'subtle')); title.append(left, tag(data.bundle.status, data.bundle.status)); caseElement.append(title);
      const notice = node('p', '', 'subtle'); notice.id = 'notice'; caseElement.append(notice);
      const overview = node('div', undefined, 'grid two');
      const findings = node('section', undefined, 'card stack'); findings.append(node('h2', `Findings (${data.discrepancies.length})`)); if (!data.discrepancies.length) findings.append(node('p', 'No deterministic discrepancies found.', 'subtle')); data.discrepancies.forEach(item => { const finding = node('div', undefined, `finding ${item.severity}`); finding.append(node('div', undefined, 'row'), node('strong', item.discrepancy_type), tag(item.severity, item.severity)); finding.append(node('p', item.message)); findings.append(finding); }); overview.append(findings);
      const decision = node('section', undefined, 'card'); decision.append(node('h2', 'Record case decision')); const decisionForm = document.createElement('form'); decisionForm.append(formField('Action', selectField('action', [['approved','Approve'], ['rejected','Reject'], ['needs_info','Needs information']])), formField('Actor', inputField('actor', 'reviewer@example.com')), formField('Reason', textAreaField('reason', 'Explain the review decision.'))); const decisionButton = node('button', 'Record decision'); decisionButton.type='submit'; decisionForm.append(decisionButton); decisionForm.onsubmit = async event => { event.preventDefault(); try { const form = new FormData(decisionForm); await request(`/bundles/${data.bundle.id}/decision`, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(Object.fromEntries(form))}); notice.textContent='Decision recorded in the audit trail.'; await loadQueue(); await loadCase(); } catch (error) { notice.textContent=error.message; } }; decision.append(decisionForm); overview.append(decision); caseElement.append(overview);
      const documentsCard = node('section', undefined, 'card stack'); documentsCard.append(node('h2', `Documents (${data.documents.length})`)); data.documents.forEach(document => { const doc = node('article', undefined, 'card'); const head = node('div', undefined, 'row between'); const docName = node('div'); docName.append(node('h3', document.original_filename), node('p', `${document.document_type} · ${document.processing_status}`, 'subtle')); head.append(docName, tag(document.extraction?.quality_status || 'not extracted')); doc.append(head); if (document.fields) doc.append(fieldTable(document.fields)); const evidence = node('details'); evidence.append(node('summary', 'Raw extracted evidence')); evidence.append(node('pre', document.extraction?.text_content || 'No extracted text is available.')); doc.append(evidence); documentsCard.append(doc); }); caseElement.append(documentsCard);
      caseElement.append(correctionPanel(data, notice));
      const audit = node('section', undefined, 'card stack'); audit.append(node('h2', `Audit history (${data.audit_events.length})`)); if (!data.audit_events.length) audit.append(node('p', 'No human action has been recorded yet.', 'subtle')); data.audit_events.forEach(event => { const entry=node('div', undefined, 'finding'); entry.append(node('strong', `${event.event_type}: ${event.action}`), node('p', `${event.actor} · ${new Date(event.created_at).toLocaleString()}`, 'subtle'), node('p', event.reason || 'No reason recorded.')); audit.append(entry); }); caseElement.append(audit);
    }
    function formField(labelText, control) { const label=node('label', labelText); label.append(control); return label; }
    function inputField(name, value) { const input=document.createElement('input'); input.name=name; input.value=value; input.required=true; return input; }
    function textAreaField(name, value) { const area=document.createElement('textarea'); area.name=name; area.value=value; area.required=true; return area; }
    function selectField(name, choices) { const select=document.createElement('select'); select.name=name; choices.forEach(([value, label])=>{ const option=node('option', label); option.value=value; select.append(option); }); return select; }
    function correctionPanel(data, notice) { const panel=node('section', undefined, 'card'); panel.append(node('h2', 'Record field correction')); const form=document.createElement('form'); const documentSelect=selectField('document_id', data.documents.map(document=>[document.id, document.original_filename])); form.append(formField('Document', documentSelect), formField('Field', selectField('field_name', [['supplier_name','Supplier name'], ['document_number','Document number'], ['document_date','Document date'], ['currency','Currency'], ['total','Total']])), formField('Action', selectField('action', [['corrected','Corrected'], ['kept','Kept as extracted'], ['marked_unavailable','Marked unavailable']])), formField('New value (for corrected)', inputField('new_value', '')), formField('Actor', inputField('actor', 'reviewer@example.com')), formField('Reason', textAreaField('reason', 'Explain the correction.'))); const button=node('button','Record correction'); button.type='submit'; form.append(button); form.onsubmit=async event=>{ event.preventDefault(); try { const values=Object.fromEntries(new FormData(form)); const documentId=values.document_id; delete values.document_id; if (values.action !== 'corrected') delete values.new_value; await request(`/bundles/${data.bundle.id}/documents/${documentId}/corrections`, {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(values)}); notice.textContent='Correction recorded; original extraction remains unchanged.'; await loadCase(); } catch(error) { notice.textContent=error.message; } }; panel.append(form); return panel; }
    async function loadCase() { if (!selectedId) return; try { renderCase(await request(`/bundles/${selectedId}/review`)); } catch(error) { clear(caseElement); caseElement.append(node('p', error.message, 'empty')); } }
    document.querySelector('#refresh').onclick = () => loadQueue().then(loadCase);
    loadQueue().then(loadCase).catch(error => { clear(caseElement); caseElement.append(node('p', error.message, 'empty')); });
  </script>
</body></html>"""
