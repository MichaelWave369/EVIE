import { useState } from 'react';
import shelf from './generated/nested-shelf.json';
import { FIELDDECK_ACTIONS, inspectEvieDeckDraft, buildFieldDeckBlueprint } from './fielddeckBridge.js';
import './fielddeckHandoff.css';

const FIELDDECK_SITE='https://michaelwave369.github.io/FieldDeck/';
const readable=(s)=>s.replaceAll('_',' ').replace(/\b\w/g,ch=>ch.toUpperCase());

export default function FieldDeckHandoff(){
  const [draft,setDraft]=useState(null);
  const [selected,setSelected]=useState([]);
  const [name,setName]=useState('EVIE Review Draft');
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [prepared,setPrepared]=useState(null);
  const loadDraft=async event=>{
    const file=event.target.files?.[0];
    event.target.value='';
    setDraft(null);setPrepared(null);setError('');setNotice('');
    if(!file)return;
    if(file.size>64000){setError('EVIE draft exceeds the 64 KB limit.');return;}
    try{
      const review=inspectEvieDeckDraft(await file.text(),shelf);
      setDraft(review);
      setSelected([]);
      setNotice('EVIE design deck inspected locally. None of its cards has been assigned a FieldDeck action.');
    }catch(e){setError(e instanceof Error?e.message:'Could not read EVIE draft.');}
  };
  const add=event=>{
    const id=event.target.value;
    if(id&&selected.length<6){setSelected(old=>[...old,id]);setPrepared(null);}
    event.target.value='';
  };
  const move=(index,delta)=>{
    setSelected(old=>{
      const next=[...old],target=index+delta;
      if(target<0||target>=next.length)return old;
      [next[index],next[target]]=[next[target],next[index]];
      return next;
    });
    setPrepared(null);
  };
  const review=()=>{
    setError('');
    try{setPrepared(buildFieldDeckBlueprint(selected,name));setNotice('Default-deny FieldDeck blueprint ready. No action has been requested.');}
    catch(e){setError(e.message);}
  };
  const download=()=>{
    if(!prepared)return;
    const blob=new Blob([JSON.stringify(prepared,null,2)+'\n'],{type:'application/json'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;a.download='evie-to-fielddeck.review-blueprint.json';
    document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),0);
    setNotice('Blueprint downloaded. Import into FieldDeck for additional review. Not submitted or executed.');
  };
  return <section className="fdh-root">
    <div className="fg-overline">R11 / FIELDDECK / HUMAN-GOVERNED REVIEW</div>
    <header className="fdh-head"><div><h3>EVIE meets FieldDeck.</h3>
      <p>Bring an EVIE Sovereign Shelf design deck, then separately choose FieldDeck's three reviewed diagnostic actions. We'll export a real FieldDeck v0.5 blueprint with execution explicitly denied.</p>
    </div><span>NO AUTOMATIC ACTION MAPPING</span></header>
    <div className="fdh-notice">EVIE's 159 historical Shelf card IDs are <strong>not</strong> FieldDeck action IDs. A FieldDeck blueprint created here is your independent design, not a translation or promise that EVIE cards will execute.</div>
    <div className="fdh-layout">
      <div className="fdh-block">
        <div className="fg-overline">01 / INSPECT EVIE DESIGN DRAFT</div>
        <label className="fdh-upload">Choose exported EVIE deck JSON
          <input type="file" accept=".json,application/json" onChange={loadDraft}/>
        </label>
        {draft?<div className="fdh-loaded"><b>{draft.count} EVIE cards inspected</b><small>0 verified FieldDeck mappings · design-only</small>
          <ol>{draft.cards.slice(0,10).map(x=><li key={x.cardId}><span>{x.position+1}</span>{x.name}<small>{x.status==='bounded_adapter'?'Bounded adapter':'Archive specification'}</small></li>)}</ol>
          {draft.count>10&&<small>{draft.count-10} additional cards not shown</small>}</div>:
          <div className="fdh-empty">Export a design-only JSON from EVIE's Full Sovereign Shelf, then select it here. No file upload occurs.</div>}
      </div>
      <div className="fdh-block">
        <div className="fg-overline">02 / SELECT REVIEWED FIELDDECK ACTIONS</div>
        <label className="fdh-field">Blueprint name
          <input value={name} onChange={e=>{setName(e.target.value);setPrepared(null);}} maxLength={64}/>
        </label>
        <label className="fdh-field">Explicit reviewed action (1–6 steps)
          <select value="" onChange={add} disabled={!draft||selected.length>=6}>
            <option value="">Choose an action…</option>
            {FIELDDECK_ACTIONS.map(a=><option key={a.id} value={a.id}>{a.label}</option>)}
          </select>
        </label>
        <div className="fdh-steps">
          {selected.length===0?<p>No recipient actions selected. EVIE doesn't choose these for you.</p>:
            <ol>{selected.map((id,i)=><li key={i}>
              <b>{String(i+1).padStart(2,'0')}</b><span>{readable(id)}</span>
              <button aria-label={'Move step '+(i+1)+' up'} disabled={i===0} onClick={()=>move(i,-1)}>↑</button>
              <button aria-label={'Move step '+(i+1)+' down'} disabled={i===selected.length-1} onClick={()=>move(i,1)}>↓</button>
              <button aria-label={'Remove step '+(i+1)} onClick={()=>{setSelected(old=>old.filter((_,j)=>i!==j));setPrepared(null);}}>×</button>
            </li>)}</ol>}
        </div>
        <button className="fdh-generate" disabled={!draft||!selected.length} onClick={review}>Validate default-deny blueprint →</button>
      </div>
    </div>
    {error&&<p role="alert" className="fdh-error">{error}</p>}
    {notice&&<p role="status" className="fdh-notification">{notice}</p>}
    {prepared&&<div className="fdh-ready"><div className="fg-overline">03 / REVIEW-ONLY RECIPIENT BLUEPRINT</div>
      <div className="fdh-receipt"><span>FieldDeck version <b>{prepared.schema_version}</b></span>
        <span>Steps <b>{prepared.steps.length}</b></span>
        <span>Execution <b>DENIED</b></span>
        <span>Review <b>REQUIRED</b></span>
      </div>
      <p>This blueprint conforms to the checked-in FieldDeck parser version used by the cross-repo test. Exporting it does not import into FieldDeck or submit an authenticated IssueOps request.</p>
      <button onClick={download}>↓ Export default-deny FieldDeck blueprint</button>
      <a href={FIELDDECK_SITE} target="_blank" rel="noreferrer">Open FieldDeck for manual blueprint import ↗</a>
    </div>}
    <p className="fdh-foot">A matching reviewed FieldDeck preset may later be eligible for a separately authenticated GitHub request. This page never requests or performs that action. FieldDeck's own validator and IssueOps approval remain authoritative.</p>
  </section>;
}
