import { useMemo, useState } from 'react';
import shelf from './generated/nested-shelf.json';
import { DECK_LIMIT, getPackCards, findLinkedCard, filterCards, reviewDraft, makeDeckDraft } from './nestedLogic.js';
import './nestedShelf.css';

const names = {node:'Nodes',shard:'Shards',lesson:'Lessons',glyph:'Glyphs',crystal:'Crystals',mandate:'Mandates',ritual:'Rituals'};
const stageOrder = ['FRAME', 'LIGHT', 'EMERGE', 'MANIFEST'];
const letters = {node:'◎',shard:'◈',lesson:'▤',glyph:'✧',crystal:'◇',mandate:'⌘',ritual:'∞'};
const packIcon = {starter_deck:'✦',money_pack:'◈',visual_pack:'◉',hardware_pack:'⌗',architecture_pack:'▧',
  sovereign_living_pack:'❋',sound_pack:'♫',intelligence_pack:'◇',sovereign_all_access:'⊙'};
const readable = value => String(value||'').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const SHORT = s => s?.length > 100 ? s.slice(0,97)+'…':s;

function Status({card}) {
  return <span className={'nest-status '+(card.status==='bounded_adapter'?'nest-limited':'nest-archived')}>
    <i/>{card.status==='bounded_adapter'?'LIMITED CAD BRIDGE':'ARCHIVE SPEC'}
  </span>;
}
function ExportDraft({ids}) {
  const [notice,setNotice]=useState('');
  return <><button className="nest-download" disabled={!ids.length} onClick={()=>{
    try {
      const draft=makeDeckDraft(ids,shelf);
      const blob=new Blob([JSON.stringify(draft,null,2)+'\n'],{type:'application/json'});
      const url=URL.createObjectURL(blob);
      const a=document.createElement('a');
      a.download='evie-deck-design-only.json';a.href=url;document.body.appendChild(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),0);
      setNotice('Draft saved locally. This file never executes cards.');
    } catch(e) {setNotice(e.message);}
  }}>↓ Export design-only JSON</button>{notice&&<span className="nest-notice" role="status">{notice}</span>}</>;
}
function ShelfCard({card,onOpen,onAdd,inDeck}) {
  return <article className="nest-card">
    <button className="nest-card-main" onClick={()=>onOpen(card)}>
      <div className="nest-card-symbol"><b>{letters[card.cardClass]||'◈'}</b><span>{card.stage}</span></div>
      <span className="nest-card-kind">{readable(card.cardClass)} · {readable(card.category)}</span>
      <h3>{card.name}</h3>
      <p>{SHORT(card.tagline||card.description)}</p>
      <Status card={card}/>
    </button>
    <div className="nest-card-actions">
      <button onClick={()=>onOpen(card)}>Inspect card <span>↗</span></button>
      <button title={inDeck?'Already in deck':'Add to design draft'} onClick={()=>onAdd(card)} disabled={inDeck}>{inDeck?'Added ✓':'+ Deck'}</button>
    </div>
  </article>;
}
function CardDetails({card,onClose,onSelect,onAdd,inDeck,onWorkshop}) {
  if(!card)return null;
  const targets=Array.from(new Set([...(card.recommendedNext||[]),...(card.compatibleWith||[])])).map(slug=>findLinkedCard(shelf,slug)).filter(Boolean);
  const sequences=(card.sequence||[]).map(slug=>findLinkedCard(shelf,slug));
  return <div className="nest-shade" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}>
    <aside className="nest-details" role="dialog" aria-modal="true" aria-labelledby="nest-detail-title">
      <div className="nest-details-head"><span className="nest-crumb">SOVEREIGN SHELF / {readable(card.packId)}</span><button onClick={onClose} className="nest-close" aria-label="Close card details">×</button></div>
      <div className="nest-detail-seal">{letters[card.cardClass]}</div>
      <div className="nest-card-kind">{card.cardClass.toUpperCase()} · {card.stage} · {card.rarity?.toUpperCase()}</div>
      <h2 id="nest-detail-title">{card.name}</h2>
      <Status card={card}/>
      <p className="nest-detail-desc">{card.description||card.tagline||'Recovered card specification.'}</p>
      <div className="nest-contract"><h3>Original card contract</h3><div><small>REQUIRES</small>{card.inputs.length?<div className="nest-tokens">{card.inputs.map((v,i)=><code key={i}>{v}</code>)}</div>:<p>None declared</p>}</div><div><small>HISTORICAL OUTPUTS</small>{card.outputs.length?<div className="nest-tokens">{card.outputs.map((v,i)=><code key={i}>{v}</code>)}</div>:<p>None declared</p>}</div></div>
      {card.status==='bounded_adapter'&&<section className="nest-adapter-truth"><b>Current bounded capability</b><p>New EVIE generator creates an OpenBlueprint concept JSON and checksum. It does <strong>not</strong> implement this historical card's structure_spec input or DXF/SVG outputs.</p><button onClick={()=>{onClose();onWorkshop()}}>Explore CAD workshop →</button></section>}
      {sequences.length>0&&<div className="nest-detail-block"><h3>Nested sequence · {sequences.filter(Boolean).length} linked steps</h3><div className="nest-sequence">{sequences.map((linked,i)=><button key={i} disabled={!linked} onClick={()=>linked&&onSelect(linked)}><span>{String(i+1).padStart(2,'0')}</span>{linked?linked.name:(card.sequence[i]+' · not in archive')}<em>↗</em></button>)}</div></div>}
      {targets.length>0&&<div className="nest-detail-block"><h3>Compatible & recommended cards</h3><p>Relationships from the historical registry; compatibility does not guarantee executable interoperability.</p><div className="nest-links">{targets.map(t=><button key={t.id} onClick={()=>onSelect(t)}><span>{t.name}</span>↗</button>)}</div></div>}
      <div className="nest-detail-footer"><button className="nest-download" disabled={inDeck} onClick={()=>onAdd(card)}>{inDeck?'Added to draft ✓':'+ Add to deck draft'}</button><small>Archive claims are unverified. No card is executed here.</small></div>
    </aside>
  </div>;
}
function DraftPanel({ids,setIds,openCard,expanded,setExpanded}) {
  const report=useMemo(()=>reviewDraft(ids,shelf.cards),[ids]);
  const remove=index=>setIds(old=>old.filter((_,i)=>i!==index));
  const move=(index,dir)=>setIds(old=>{const next=[...old],j=index+dir;if(j<0||j>=next.length)return old;[next[j],next[index]]=[next[index],next[j]];return next});
  return <section className={'nest-draft '+(expanded?'nest-draft-open':'')}>
    <div className="nest-draft-title"><div><span className="nest-overline">COMPOSE / DESIGN ONLY</span><h3>Nested deck <span>{ids.length}/{DECK_LIMIT}</span></h3></div><button className="nest-draft-toggle" onClick={()=>setExpanded(v=>!v)}>{expanded?'Hide':'View'} ↕</button></div>
    <div className="nest-draft-inner">
      <p>Connect cards into a proposed chain. Review missing inputs and export a draft. <strong>Execution is disabled.</strong></p>
      {ids.length===0?<div className="nest-empty-draft">◌<span>Your deck is empty.<br/>Add cards from the shelf to begin.</span></div>:
        <ol className="nest-deck-list">{ids.map((id,i)=>{const card=findLinkedCard(shelf,id),step=report.steps[i];return <li key={id}><div className="nest-deck-index">{String(i+1).padStart(2,'0')}</div><div className="nest-deck-item"><button onClick={()=>openCard(card)}>{card?.name||id}</button><small>{step.missing.length?'Needs: '+step.missing.join(', '):'Inputs matched in draft'} · NOT RUNNABLE</small></div><div className="nest-deck-buttons"><button onClick={()=>move(i,-1)} disabled={i===0} aria-label={'Move '+(card?.name||id)+' up'}>↑</button><button onClick={()=>move(i,1)} disabled={i===ids.length-1} aria-label={'Move '+(card?.name||id)+' down'}>↓</button><button onClick={()=>remove(i)} aria-label={'Remove '+(card?.name||id)}>×</button></div></li>})}</ol>}
      <div className="nest-deck-check"><span>Dependency gaps: <b>{report.unresolved}</b></span><span>Unverified steps: <b>{report.unverified}</b></span></div>
      <ExportDraft ids={ids}/>
      {ids.length>0&&<button className="nest-clear" onClick={()=>setIds([])}>Clear design draft</button>}
      <p className="nest-draft-footnote">No EVIE API calls, no private vault, no auto-dispatch. Matching is advisory, not engineering validation.</p>
    </div>
  </section>;
}
export default function NestedShelf({onWorkshop}) {
  const [packId,setPackId]=useState('sovereign_all_access');
  const [query,setQuery]=useState('');
  const [cardClass,setCardClass]=useState('all');
  const [stage,setStage]=useState('all');
  const [category,setCategory]=useState('all');
  const [selected,setSelected]=useState(null);
  const [deck,setDeck]=useState([]);
  const [draftExpanded,setDraftExpanded]=useState(false);
  const [visible,setVisible]=useState(30);
  const [notice,setNotice]=useState('');
  const pack=shelf.packs.find(p=>p.id===packId);
  const packCards=useMemo(()=>getPackCards(shelf,packId),[packId]);
  const categories=[...new Set(packCards.map(c=>c.category))].sort();
  const filtered=useMemo(()=>filterCards(packCards,{query,cardClass,stage,category}),[packCards,query,cardClass,stage,category]);
  const activeCards=filtered.slice(0,visible);
  const add=(card)=>{
    if(deck.includes(card.id)){setNotice('Card is already in the draft.');return;}
    if(deck.length>=DECK_LIMIT){setNotice('The public draft is limited to 32 cards.');return;}
    setDeck(current=>[...current,card.id]);setNotice(card.name+' added to the design-only draft.');
    setDraftExpanded(true);
  };
  const choosePack=id=>{setPackId(id);setQuery('');setCardClass('all');setStage('all');setCategory('all');setVisible(30);setNotice('')};
  return <div className="nest-page">
    <header className="nest-hero"><div><span className="nest-overline">EVIE COMMONS / EVIE WITHIN EVIE</span><h1>The Nested <em>Sovereign Shelf.</em></h1><p>Enter a pack. Open a card. Follow its connections. Nest entire workflows inside workflows. Explore the recovered archive without granting execution authority.</p><div className="nest-metrics"><span><b>{shelf.cards.length}</b> Cards</span><span><b>{shelf.packs.length}</b> Packs</span><span><b>{new Set(shelf.cards.map(c=>c.cardClass)).size}</b> Classes</span></div></div><div className="nest-hero-art" aria-hidden="true"><div className="nest-ring r1"><div className="nest-ring r2"><div className="nest-ring r3"><span>✦</span></div></div></div><small>CARDS WITHIN PACKS<br/>PACKS WITHIN EVIE</small></div></header>
    <div className="nest-caution"><span>◎ ARCHIVE TRANSPARENCY</span> Original descriptions and outputs are historical specifications, not verified executable features. The only bounded adapter currently linked is the concept-JSON floor-plan producer.</div>
    <div className="nest-layout">
      <aside className="nest-pack-rail"><div className="nest-pack-heading">01 / CHOOSE A NEST <span>↘</span></div>{shelf.packs.map(p=>{const count=getPackCards(shelf,p.id).length;return <button key={p.id} onClick={()=>choosePack(p.id)} className={'nest-pack '+(packId===p.id?'active':'')}><span className="nest-pack-emblem">{packIcon[p.id]||'◈'}</span><span className="nest-pack-info"><b>{p.name}</b><small>{p.id==='sovereign_all_access'?'All archive cards':p.tagline}</small></span><span className="nest-pack-count">{count}</span></button>})}<p>Pack membership follows the historical registry. Counts reflect actual referenced cards, not advertised card quotas.</p></aside>
      <div className="nest-explore"><nav className="nest-breadcrumb" aria-label="Nested Shelf location"><button onClick={()=>choosePack('sovereign_all_access')}>⊙ FULL SHELF</button><span>/</span><b>{pack?.name}</b>{cardClass!=='all'&&<><span>/</span><b>{readable(cardClass)}</b></>}</nav>
        <div className="nest-explore-title"><div><span className="nest-overline">02 / BROWSE INSIDE</span><h2>{pack?.name}</h2><p>{pack?.description || 'Explore the full historic card collection.'}</p></div><span className="nest-result-num">{filtered.length}<small>VISIBLE MATCHES</small></span></div>
        <div className="nest-filters"><label className="nest-search"><span>⌕</span><input placeholder="Search 159 cards, contract fields, names..." aria-label="Search nested shelf" value={query} onChange={e=>{setQuery(e.target.value);setVisible(30)}} /></label><label><span>CLASS</span><select aria-label="Filter class" value={cardClass} onChange={e=>{setCardClass(e.target.value);setVisible(30)}}><option value="all">All types</option>{Object.keys(names).map(k=><option key={k} value={k}>{names[k]}</option>)}</select></label><label><span>STAGE</span><select aria-label="Filter stage" value={stage} onChange={e=>{setStage(e.target.value);setVisible(30)}}><option value="all">All stages</option>{stageOrder.map(k=><option key={k} value={k}>{k}</option>)}</select></label></div>
        <div className="nest-class-tabs" role="group" aria-label="Filter by card class"><button className={cardClass==='all'?'on':''} onClick={()=>{setCardClass('all');setVisible(30)}}>All {packCards.length}</button>{Object.entries(names).map(([k,v])=>{const n=packCards.filter(c=>c.cardClass===k).length;return n>0&&<button key={k} className={cardClass===k?'on':''} onClick={()=>{setCardClass(k);setVisible(30)}}>{v} <span>{n}</span></button>})}</div>
        {categories.length>1&&<div className="nest-categories"><label htmlFor="nest-category">CATEGORY</label><select id="nest-category" value={category} onChange={e=>{setCategory(e.target.value);setVisible(30)}}><option value="all">All categories</option>{categories.map(c=><option key={c} value={c}>{readable(c)}</option>)}</select></div>}
        <div className="nest-count-line">{activeCards.length} of {filtered.length} matching cards · click a card to open nested connections</div>
        {filtered.length?<div className="nest-grid">{activeCards.map(c=><ShelfCard key={c.id} card={c} onOpen={setSelected} onAdd={add} inDeck={deck.includes(c.id)}/>)}</div>:<div className="nest-no-results">No cards match these filters. <button onClick={()=>{setQuery('');setCardClass('all');setStage('all');setCategory('all')}}>Clear filters</button></div>}
        {visible<filtered.length&&<button className="nest-more" onClick={()=>setVisible(v=>v+30)}>Show more cards ({filtered.length-visible} remaining) ↓</button>}
        <div className="nest-legacy-note">SOURCE · Sovereign Shelf registry v{shelf.source.version} · Original SHA-256 recorded · Curated public snapshot, not the full private record.</div>
      </div>
      <DraftPanel ids={deck} setIds={setDeck} openCard={setSelected} expanded={draftExpanded} setExpanded={setDraftExpanded}/>
    </div>
    {notice&&<div className="nest-toast" role="status" onClick={()=>setNotice('')}>{notice} ×</div>}
    <CardDetails card={selected} onClose={()=>setSelected(null)} onSelect={setSelected} onAdd={add} inDeck={selected ? deck.includes(selected.id):false} onWorkshop={onWorkshop}/>
  </div>;
}
