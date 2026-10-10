import { useMemo, useState } from 'react';
import manifest from './generated/mission-control.json';
import { availablePlanFlags, planEvieWorkflow } from './workflowPlan.js';
import './workflowStudio.css';

const pretty = value => String(value).replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const display = value => {
  if(value==='candidate_only') return 'PLANNED · NOT AUTHORIZED';
  if(value==='skipped_by_default') return 'SKIPPED BY FLAG';
  return value;
};
const recommended = [
  'openblueprint_concept_floor_plan',
  'vault_to_lesson_pack',
  'youtube_flywheel',
  'vault_to_money_pack',
  'vault_to_money_publish'
];

export default function WorkflowStudio(){
  const [name,setName]=useState('openblueprint_concept_floor_plan');
  const [flags,setFlags]=useState([]);
  const [message,setMessage]=useState('');
  const options=useMemo(()=>[...manifest.workflows].sort((a,b)=>{
    const ai=recommended.indexOf(a.id),bi=recommended.indexOf(b.id);
    return (ai===-1?999:ai)-(bi===-1?999:bi)||a.id.localeCompare(b.id);
  }),[]);
  const flagOptions=useMemo(()=>availablePlanFlags(manifest,name),[name]);
  const plan=useMemo(()=>{
    try{return{result:planEvieWorkflow(manifest,name,flags),error:null};}
    catch(e){return{result:null,error:e instanceof Error?e.message:'Invalid workflow plan'};}
  },[name,flags]);
  const changeName=value=>{
    setName(value);setFlags([]);setMessage('');
  };
  const toggle=flag=>{
    setFlags(old=>old.includes(flag)?old.filter(x=>x!==flag):[...old,flag]);
    setMessage('');
  };
  const save=()=>{
    if(!plan.result)return;
    const bytes=JSON.stringify(plan.result,null,2)+'\n';
    const obj=new Blob([bytes],{type:'application/json'});
    const url=URL.createObjectURL(obj);
    const a=document.createElement('a');
    a.href=url;a.download='evie-workflow-preflight.review-only.json';
    document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),0);
    setMessage('Read-only plan downloaded. No job was queued or authorized.');
  };
  const command='python -m app.workflows.preflight --workflow '+name+
    flags.map(flag=>' --enable '+flag).join('');
  const copy=async()=>{
    try{await navigator.clipboard.writeText(command);setMessage('Local Python command copied. It reads source files only.');}
    catch{setMessage('Clipboard unavailable; select the command text manually.');}
  };
  const active=plan.result?.steps.filter(s=>s.kind==='module'&&s.decision==='candidate_only')||[];
  const flagsSelected=flags.length;
  const current=manifest.workflows.find(w=>w.id===name);
  return <section className="ws-root">
    <header className="ws-top">
      <div className="mc-overline">EVIE / R12 / REAL WORKFLOW PREFLIGHT</div>
      <div className="ws-heading"><div><h2>Workflow <em>Revival Studio.</em></h2>
        <p>EVIE already has ten real configured workflows. Explore their nested steps, simulate optional branches, and discover the permissions they'll need before a single module can run.</p></div>
        <div className="ws-seal" aria-hidden="true">⌘</div></div>
      <div className="ws-banner">NO RUN RECORD · NO DATABASE WRITE · NO MODEL CALLS · NO EXECUTION</div>
    </header>
    <div className="ws-columns">
      <div className="ws-settings">
        <div className="mc-overline">01 / SELECT ACTUAL EVIE WORKFLOW</div>
        <label className="ws-select-label">Configured workflow
          <select value={name} onChange={e=>changeName(e.target.value)}>
            {options.map(option=><option key={option.id} value={option.id}>{pretty(option.id)}</option>)}
          </select></label>
        <p className="ws-description">{current?.description}</p>
        <div className="ws-trace">
          <span>SOURCE CONTROL</span><code>{manifest.source.sha256.slice(0,20)}…</code>
          <small>Generated from checked-in Python module registry and workflow JSON</small>
        </div>
        <div className="ws-options">
          <div className="mc-overline">02 / OPTIONAL BRANCHES</div>
          {flagOptions.length>0?<><p>Select which conditions to include in the <strong>simulation</strong>. Switching one on does not enable the actual module or service.</p>
            {flagOptions.map(flag=><label className="ws-toggle" key={flag}>
              <input type="checkbox" checked={flags.includes(flag)} onChange={()=>toggle(flag)}/>
              <span>{pretty(flag)}<small>{/publish|gumroad|youtube|short_form|thread_bomber|cross_pollination/.test(flag)?'External-effects review may be required':'Simulate optional branch only'}</small></span>
            </label>)}</>
            :<p>This workflow defines no optional constraint flags.</p>}
        </div>
        <div className="ws-cli">
          <div className="mc-overline">LOCAL SOURCE-ONLY INSPECTION</div>
          <code>{command}</code>
          <button onClick={copy}>Copy CLI command ↗</button>
        </div>
      </div>
      <div className="ws-results">
        <div className="mc-overline">03 / WORKFLOW EXPANSION LEDGER</div>
        {plan.error?<p role="alert" className="ws-error">{plan.error}</p>:
        <>
          <div className="ws-metrics">
            <div><b>{plan.result.summary.planRows}</b><small>Expanded rows</small></div>
            <div><b>{active.length}</b><small>Candidate modules</small></div>
            <div><b>{plan.result.summary.skippedRows}</b><small>Skipped branches</small></div>
            <div><b>{plan.result.summary.effectReviewCandidates}</b><small>Effect-risk hints</small></div>
          </div>
          <div className="ws-ledger">
            {plan.result.steps.map((step,index)=>{
              const nested=step.kind==='nested',inactive=step.decision==='skipped_by_default';
              const indent=Math.min(3,step.path.split('/').length/2-1);
              return <div key={step.path+'-'+index} className={'ws-step '+(inactive?'inactive':'')}
                style={{'--ws-depth':Math.max(0,indent)}}>
                <div className="ws-index">{String(index+1).padStart(2,'0')}</div>
                <div className="ws-info"><div className="ws-step-title">{nested?'⌘ ': '◈ '}{pretty(step.name)}</div>
                  <div className="ws-step-meta">{nested?'NESTED WORKFLOW':'PYTHON MODULE'} · {display(step.decision)}</div>
                  {step.condition&&<small>Condition: {step.condition} · {flags.includes(step.condition)?'SIMULATED ON':'DEFAULT OFF'}</small>}
                </div>
                {step.effectReview&&<span className="ws-risk">REVIEW EFFECTS</span>}
              </div>;
            })}
          </div>
          <div className="ws-report">
            <h3>Planning only. Not authorization.</h3>
            <p>All candidate steps still require dependency checks, budgets, isolation and an independently approved execution lease. Effect-risk hints are based on module names, not a security audit. The original EVIE runner is <strong>not called</strong>.</p>
            <div className="ws-results-actions"><button onClick={save}>↓ Export source-bound review plan</button>
              <span>Execution: DENIED · Database: UNTOUCHED</span></div>
          </div>
        </>}
        {message&&<p role="status" className="ws-feedback">{message}</p>}
      </div>
    </div>
  </section>;
}
