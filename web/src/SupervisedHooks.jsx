import { useState } from 'react';
import manifest from './generated/mission-control.json';
import { inspectHooksReceipt } from './hooksReview.js';
import './supervisedHooks.css';

const COMMAND = 'python -m tools.evie_supervised_hooks local_content_hooks_review --script-file ./draft.txt --topic "EVIE Creator Loop" --stage-dir ../evie-hooks-review-001 --confirm-local-execution';

export default function SupervisedHooks(){
 const [receipt,setReceipt]=useState(null);
 const [hooks,setHooks]=useState(null);
 const [script,setScript]=useState(null);
 const [result,setResult]=useState(null);
 const [error,setError]=useState('');
 const [message,setMessage]=useState('');
 const [busy,setBusy]=useState(false);
 const choose=(setter,event)=>{setter(event.target.files?.[0]||null);setResult(null);setError('');};
 const copy=async()=>{
   try{await navigator.clipboard.writeText(COMMAND);setMessage('Copied. Edit the topic, script location and NEW output folder before running.');}
   catch{setMessage('Clipboard unavailable. Select and copy the command manually.');}
 };
 const review=async()=>{
   if(!receipt||!hooks)return;
   setBusy(true);setError('');setResult(null);
   try{
     if(receipt.size>32000||hooks.size>32768||(script&&script.size>8192))
       throw Error('Selected review files exceed local limits.');
     setResult(await inspectHooksReceipt(await receipt.text(),await hooks.arrayBuffer(),
       manifest,script?await script.arrayBuffer():null));
     setMessage('All checks ran inside this browser. No data was uploaded.');
   }catch(e){setError(e instanceof Error?e.message:'Review could not be verified.');}
   finally{setBusy(false);}
 };
 return <section className="sh-root">
   <div className="mc-overline">R14 / FIRST LOCAL CONTENT WORKFLOW / REAL EVIE V2 GENERATOR</div>
   <header className="sh-head"><h3>Nine-Hook Content Workshop</h3>
    <p>Turn a short script into nine reviewable content hooks using EVIE's original template-based HooksGenerator. Real local production, no model API, no publishing.</p>
   </header>
   <div className="sh-limits"><span>1 ALLOWLISTED MODULE</span><span>8 KB SCRIPT INPUT</span><span>20 SEC TIMEOUT</span><span>NO PUBLISHING</span></div>
   <div className="sh-command"><span>RUN MANUALLY ON YOUR PC · FROM EVIE REPO ROOT</span>
     <code>{COMMAND}</code><button onClick={copy}>Copy local command</button></div>
   <p className="sh-foot">First create <code>draft.txt</code> with at least 20 bytes of your own script or notes. The command requires explicit confirmation, refuses existing staging folders and saves its four review files outside Git. You can change the topic and paths within the documented limits. The subprocess is not a hard OS sandbox: run trusted code only.</p>
   <div className="mc-overline">BROWSER-ONLY REVIEW</div>
   <div className="sh-uploads">
    <label>01 / review-receipt.json <input type="file" accept=".json,application/json" onChange={e=>choose(setReceipt,e)}/></label>
    <label>02 / nine-hooks.json <input type="file" accept=".json,application/json" onChange={e=>choose(setHooks,e)}/></label>
    <label>03 / Original script (optional) <input type="file" accept=".txt,text/plain" onChange={e=>choose(setScript,e)}/></label>
   </div>
   <button className="sh-check" disabled={!receipt||!hooks||busy} onClick={review}>{busy?'Checking locally…':'Inspect nine-hook review bundle →'}</button>
   {message&&<p role="status" className="sh-status">{message}</p>}
   {error&&<p role="alert" className="sh-error">{error}</p>}
   {result&&<div className="sh-output">
     <div className="sh-pass">✓ Matched the local content review format · Source + artifact SHA-256 consistent</div>
     <h4>{result.topic}</h4>
     {['educational','controversial','curiosity'].map(category=><div className="sh-category" key={category}>
       <h5>{category} <span>3 hooks</span></h5>
       <ol>{result.categories[category].map((line,i)=><li key={i}>{line}</li>)}</ol>
     </div>)}
     <p>Unsigned local observation. {result.inputMatched?'The original script hash also matches.':'The original input script has not been independently compared.'} These hooks can contain template hype; edit and fact-check before using them. No publishing, authentication, or future execution permission is granted.</p>
   </div>}
 </section>;
}
