import { useMemo, useState } from 'react';
import manifest from './generated/mission-control.json';
import QualificationLab from './QualificationLab.jsx';
import WorkflowStudio from './WorkflowStudio.jsx';
import './missionControl.css';

const GH = 'https://github.com/MichaelWave369/EVIE';
const command = 'python -m tools.evie_doctor --json --smoke-cad';
const pretty = x => x.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const GROUPS = [...new Set(manifest.modules.map(x => x.group))].sort();
const format = n => String(n).padStart(2, '0');

function Evidence({ module }) {
  return module.evidence.level === 'targeted_test_source'
    ? <span className="mc-evidence mc-source"><i/> TEST SOURCE EXISTS</span>
    : <span className="mc-evidence mc-reg"><i/> REGISTERED ONLY</span>;
}

function ModuleDetail({ module, onClose, openWorkflow }) {
  if (!module) return null;
  return <div className="mc-shade" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
    <section className="mc-drawer" role="dialog" aria-modal="true" aria-labelledby="mc-detail-title">
      <div className="mc-drawer-top"><span>CAPABILITY / SOURCE INSPECTION</span><button onClick={onClose} aria-label="Close module details">×</button></div>
      <div className="mc-drawer-sigil">◈</div>
      <p className="mc-mono">{module.group.toUpperCase()} / PYTHON MODULE</p>
      <h2 id="mc-detail-title">{pretty(module.id)}</h2>
      <Evidence module={module}/>
      <div className="mc-facts">
        <div><span>Registry key</span><code>{module.id}</code></div>
        <div><span>Python class</span><code>{module.className}</code></div>
        <div><span>Referenced by</span><b>{module.workflowRefs.length} configured workflows</b></div>
        <div><span>Live qualification</span><b>NOT VERIFIED</b></div>
        <div><span>External-effects review</span><b>{module.effectfulReviewFlag ? 'Review advised (name heuristic)' : 'No naming flag; not audited'}</b></div>
      </div>
      <div className="mc-drawer-section"><h3>Evidence</h3><p>{module.evidence.description}</p>
        {module.evidence.path && <a href={GH + '/blob/main/' + module.evidence.path} target="_blank" rel="noreferrer">{module.evidence.path} ↗</a>}
      </div>
      <div className="mc-drawer-section"><h3>Workflow references</h3>
        {module.workflowRefs.length ? <div className="mc-ref-links">{module.workflowRefs.map(id => <button key={id} onClick={() => { onClose(); openWorkflow(id); }}>{pretty(id)} <span>↗</span></button>)}</div>
          : <p>No configured workflow references this module directly. It may be callable independently; no execution claim.</p>}
      </div>
      <div className="mc-drawer-section"><h3>Operator notes</h3><p>Registration is not proof of a working provider, installed dependency, correct environment, or a successful run. Use the local EVIE Doctor for limited diagnostics and verify individual module outputs before approving external effects.</p></div>
      <a className="mc-drawer-link" href={GH + '/blob/main/app/modules/__init__.py'} target="_blank" rel="noreferrer">Inspect source registry ↗</a>
    </section>
  </div>;
}

function WorkflowDetail({ workflow, onClose, openModule }) {
  if (!workflow) return null;
  return <div className="mc-shade" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
    <section className="mc-drawer" role="dialog" aria-modal="true" aria-labelledby="mc-wf-title">
      <div className="mc-drawer-top"><span>WORKFLOW / CONFIGURED BLUEPRINT</span><button onClick={onClose} aria-label="Close workflow details">×</button></div>
      <div className="mc-drawer-sigil">⌘</div><p className="mc-mono">REGISTRY RECORD / NOT EXECUTED</p>
      <h2 id="mc-wf-title">{pretty(workflow.id)}</h2>
      <p className="mc-description">{workflow.description}</p>
      <span className="mc-evidence mc-reg"><i/> CONFIGURED ONLY</span>
      <div className="mc-facts"><div><span>Steps</span><b>{workflow.steps.length}</b></div>
        <div><span>Referenced modules</span><b>{workflow.modules.length}</b></div>
        <div><span>Reference errors</span><b>{workflow.referenceIssues.length}</b></div>
        <div><span>Live run evidence</span><b>NOT VERIFIED</b></div></div>
      <div className="mc-drawer-section"><h3>Ordered steps</h3>
        <ol className="mc-wf-steps">{workflow.steps.map(step => <li key={step.index}>
          <span className="mc-step-number">{format(step.index)}</span><div>
            <span>{step.module ? 'MODULE' : 'NESTED WORKFLOW'}{step.optional ? ' / OPTIONAL' : ''}</span>
            {step.module ? <button onClick={() => { onClose(); openModule(step.module); }}>{pretty(step.module)} ↗</button>
              : <strong>{pretty(step.workflow || 'invalid step')}</strong>}
          </div>
        </li>)}</ol>
        {workflow.referenceIssues.length > 0 && <div className="mc-issues">{workflow.referenceIssues.join(' · ')}</div>}
      </div>
      <div className="mc-drawer-section"><p>These steps describe a configured recipe. No browser code invokes the workflow or sends credentials to EVIE.</p></div>
      <a className="mc-drawer-link" href={GH + '/blob/main/configs/workflows.json'} target="_blank" rel="noreferrer">Inspect workflow registry ↗</a>
    </section>
  </div>;
}

export default function MissionControl() {
  const [tab, setTab] = useState('modules');
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState('all');
  const [qualification, setQualification] = useState('all');
  const [module, setModule] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [show, setShow] = useState(36);
  const [copyMessage, setCopyMessage] = useState('');

  const modules = useMemo(() => manifest.modules.filter(item => {
    const normalized = query.trim().toLowerCase();
    const match = [item.id, item.className, item.group, ...item.workflowRefs].join(' ').toLowerCase();
    return (group === 'all' || item.group === group)
      && (qualification === 'all' || (qualification === 'source_test' ? item.evidence.level === 'targeted_test_source'
        : qualification === 'workflow' ? item.workflowRefs.length > 0 : item.effectfulReviewFlag))
      && (!normalized || match.includes(normalized));
  }), [query, group, qualification]);

  const flows = useMemo(() => manifest.workflows.filter(w =>
    !query.trim() || [w.id, w.description, ...w.modules, ...w.nestedWorkflows, ...w.tags]
      .join(' ').toLowerCase().includes(query.trim().toLowerCase())), [query]);

  const choose = next => { setTab(next); setQuery(''); setGroup('all'); setQualification('all'); setShow(36); };
  const openWorkflow = id => { setTab('workflows'); setWorkflow(manifest.workflows.find(w => w.id === id) || null); };
  const openModule = id => { setTab('modules'); setModule(manifest.modules.find(m => m.id === id) || null); };
  const copyCommand = () => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(command).then(() => setCopyMessage('Command copied. Run it on your own EVIE machine.'))
        .catch(() => setCopyMessage('Copy unavailable. Select the command text manually.'));
    } else setCopyMessage('Select the command text manually.');
  };

  return <div className="mc-page">
    <header className="mc-hero">
      <div className="mc-overline"><i/> EVIE COMMONS / REALITY LEDGER / R6</div>
      <div className="mc-hero-flex"><div><h1>Capability <em>Mission Control.</em></h1>
        <p>A source-grounded map of the real EVIE engine. Explore the modules, trace configured workflows, and identify what still needs qualification before anyone gives the machines permission to do things.</p>
      </div><div className="mc-radar" aria-hidden="true"><div><div><div>✦</div></div></div><span>REGISTRY <b>≠</b> VERIFIED</span></div></div>
      <div className="mc-metrics">
        <div><span>REGISTERED MODULES</span><strong>{manifest.summary.registeredModules}</strong><small>From Python source</small></div>
        <div><span>CONFIGURED WORKFLOWS</span><strong>{format(manifest.summary.configuredWorkflows)}</strong><small>From registry JSON</small></div>
        <div><span>MODULES REFERENCED</span><strong>{manifest.summary.directlyUsedModules}</strong><small>Direct workflow references</small></div>
        <div><span>LIVE-QUALIFIED</span><strong>{format(manifest.summary.runtimeQualifiedModules)}</strong><small>Not verified on this machine</small></div>
      </div>
    </header>
    <section className="mc-truth"><div className="mc-truth-symbol">◎</div><div><b>This is a static source inventory, not a live status monitor.</b><p>Module registrations, configured workflows, and targeted test files can be indexed without running a provider. No green availability badges, model access, key inspection, or private API connection from GitHub Pages.</p></div></section>
    <div className="mc-body">
      <div className="mc-switch"><button className={tab === 'modules' ? 'active' : ''} onClick={() => choose('modules')}>◈ Modules <span>{manifest.summary.registeredModules}</span></button><button className={tab === 'workflows' ? 'active' : ''} onClick={() => choose('workflows')}>⌘ Workflows <span>{manifest.summary.configuredWorkflows}</span></button><button className={tab === 'studio' ? 'active' : ''} onClick={() => choose('studio')}>⌘ Workflow Studio <span>R12</span></button><button className={tab === 'lab' ? 'active' : ''} onClick={() => choose('lab')}>⌗ Qualification Lab <span>01</span></button></div>
      {tab === 'lab' ? <QualificationLab/> : tab === 'studio' ? <WorkflowStudio/> : <><div className="mc-section-title"><div><div className="mc-overline">INVENTORY / READ-ONLY INSPECTION</div><h2>{tab === 'modules' ? 'Python capability roster' : 'Workflow dependency graph'}</h2></div><span>SHA-256 · {manifest.source.sha256.slice(0, 12)}…</span></div>
      <div className="mc-controls"><label className="mc-search">⌕<input value={query} onChange={e => { setQuery(e.target.value); setShow(36); }} placeholder={tab === 'modules' ? 'Search modules, classes and workflow references…' : 'Search workflow steps and tags…'} aria-label={'Search ' + tab}/></label>
        {tab === 'modules' && <><select aria-label="Filter module group" value={group} onChange={e => { setGroup(e.target.value); setShow(36); }}><option value="all">All groups</option>{GROUPS.map(g => <option key={g} value={g}>{g}</option>)}</select>
          <select aria-label="Filter module evidence" value={qualification} onChange={e => { setQualification(e.target.value); setShow(36); }}>
            <option value="all">Any evidence</option><option value="source_test">Targeted test source</option>
            <option value="workflow">Used by workflow</option><option value="effects">Effect-review flag</option>
          </select></>}
      </div>
      <p className="mc-result-label">{tab === 'modules' ? modules.length + ' modules match' : flows.length + ' workflows match'} · Select a record to inspect source and dependencies</p>
      {tab === 'modules' && <><div className="mc-grid">{modules.slice(0, show).map(item => <button key={item.id} className="mc-tile" onClick={() => setModule(item)}>
        <div className="mc-tile-top"><span className="mc-glyph">◈</span><span>↗</span></div><small>{item.group.toUpperCase()}</small><h3>{pretty(item.id)}</h3>
        <p>{item.className}</p><div className="mc-tile-base"><Evidence module={item}/><span>{item.workflowRefs.length} FLOWS</span></div>
      </button>)}</div>
        {show < modules.length && <button className="mc-more" onClick={() => setShow(show + 36)}>Show more modules ({modules.length - show} remaining) ↓</button>}</>}
      {tab === 'workflows' && <div className="mc-flow-grid">{flows.map(w => <button key={w.id} onClick={() => setWorkflow(w)} className="mc-flow-card"><div className="mc-tile-top"><span className="mc-glyph">⌘</span><span>↗</span></div><span className="mc-mono">WORKFLOW / CONFIGURED ONLY</span><h3>{pretty(w.id)}</h3><p>{w.description}</p><div className="mc-flow-foot"><span>{w.steps.length} STEPS</span><span>{w.modules.length} MODULES</span><span>{w.referenceIssues.length} REF ISSUES</span></div></button>)}</div>}
      {((tab === 'modules' && modules.length === 0) || (tab === 'workflows' && flows.length === 0)) && <div className="mc-empty">No matching entries. Change your search or filters.</div>}
      <section className="mc-local-panel"><div className="mc-local-icon">⌘</div><div><div className="mc-overline">LOCAL ENGINE / NEXT QUALIFICATION GATE</div><h3>EVIE Doctor</h3><p>Run the offline diagnosis on your PC to inspect registration wiring and optionally perform a real, disposable CAD-producer smoke test. It does not probe the other modules or authorize publishing.</p><div className="mc-command"><code>{command}</code><button onClick={copyCommand} aria-label="Copy EVIE Doctor command">Copy ↗</button></div>{copyMessage && <small role="status">{copyMessage}</small>}</div></section>
      <div className="mc-footer-line">BUILD SOURCE · {manifest.source.files.join(' + ')} · VERIFIED RUNS ARE NOT IMPLIED BY THIS VIEW.</div></>}
    </div>
    <ModuleDetail module={module} onClose={() => setModule(null)} openWorkflow={openWorkflow}/>
    <WorkflowDetail workflow={workflow} onClose={() => setWorkflow(null)} openModule={openModule}/>
  </div>;
}
