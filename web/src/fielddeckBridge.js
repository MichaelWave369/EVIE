/** EVIE → FieldDeck review-only blueprint planner.
 *
 * The 159 Sovereign Shelf card IDs are NOT the three FieldDeck action IDs.
 * This converter NEVER infers actions from historical cards, silently maps
 * cards to executors, or dispatches IssueOps.
 */
export const EVIE_DRAFT_SCHEMA = 'evie.deck.draft/1';
export const FIELDDECK_VERSION = '0.5.0';
export const FIELDDECK_KIND = 'fielddeck.chain.blueprint';
export const MAX_DRAFT_BYTES = 64_000;
export const MAX_FIELDDECK_STEPS = 6;
export const FIELDDECK_ACTIONS = Object.freeze([
  Object.freeze({id:'catalog-health', label:'Catalog Health', description:'Reviewed catalog/registry diagnostic'}),
  Object.freeze({id:'script-smoke', label:'Script Smoke Test', description:'Reviewed deterministic diagnostic'}),
  Object.freeze({id:'macro-demo', label:'Macro Sequence', description:'Reviewed fixed macro demo'}),
]);
const ACTION_SET = new Set(FIELDDECK_ACTIONS.map(a=>a.id));
const fieldKeys = (obj,keys)=>obj && typeof obj==='object' && !Array.isArray(obj) &&
  Object.keys(obj).length===keys.length && keys.every(key=>Object.hasOwn(obj,key));
const DRAFT_KEYS = ['schemaVersion','origin','mode','createdAt','cards','validation','note'];
const DRAFT_VALIDATION_KEYS = ['unresolvedSteps','unverifiedSteps','executable'];

export function inspectEvieDeckDraft(value, shelf) {
  let raw;
  if(typeof value==='string'){
    if(new TextEncoder().encode(value).length>MAX_DRAFT_BYTES || !value.length)
      throw Error('EVIE design draft must be JSON under 64 KB.');
    try {raw=JSON.parse(value);} catch {throw Error('Malformed EVIE deck JSON.');}
  } else raw=value;
  if(!fieldKeys(raw,DRAFT_KEYS) || raw.schemaVersion!==EVIE_DRAFT_SCHEMA ||
     raw.origin!=='EVIE Commons public static Shelf' || raw.mode!=='design-only')
    throw Error('Unsupported or executable EVIE draft.');
  if(typeof raw.createdAt!=='string'||!Number.isFinite(Date.parse(raw.createdAt)) ||
     !Array.isArray(raw.cards)||raw.cards.length<1||raw.cards.length>32||
     !fieldKeys(raw.validation,DRAFT_VALIDATION_KEYS) ||
     raw.validation.executable!==false ||
     !Number.isInteger(raw.validation.unresolvedSteps)||raw.validation.unresolvedSteps<0||
     !Number.isInteger(raw.validation.unverifiedSteps)||raw.validation.unverifiedSteps<0||
     typeof raw.note!=='string'||raw.note.length>500)
    throw Error('EVIE draft bounds or default-deny validation are invalid.');
  const known = new Map(shelf?.cards?.map(c=>[c.id,c])||[]);
  const ids=new Set();
  const rows=raw.cards.map((entry,index)=>{
    if(!fieldKeys(entry,['position','cardId'])||entry.position!==index||
       typeof entry.cardId!=='string'||ids.has(entry.cardId)||!known.has(entry.cardId))
      throw Error('Unknown, duplicate or out-of-order EVIE shelf card.');
    ids.add(entry.cardId);
    const c=known.get(entry.cardId);
    return {position:index,cardId:c.id,name:c.name,status:c.status};
  });
  return {
    schemaVersion:EVIE_DRAFT_SCHEMA, cards:rows, count:rows.length,
    unresolved:raw.validation.unresolvedSteps,
    unverified:raw.validation.unverifiedSteps,
    executable:false, importedAsFieldDeckActions:0,
    note:'EVIE card IDs have no verified mapping to FieldDeck action IDs.',
  };
}

export function buildFieldDeckBlueprint(actionIds, name='EVIE Review Draft') {
  if(!Array.isArray(actionIds)||actionIds.length<1||actionIds.length>MAX_FIELDDECK_STEPS||
     !actionIds.every(id=>typeof id==='string'&&ACTION_SET.has(id)))
    throw Error('Choose 1–6 explicit FieldDeck reviewed action IDs.');
  if(typeof name!=='string'||!(/^[a-zA-Z0-9 _.-]{1,64}$/.test(name))||name.trim()!==name)
    throw Error('Name must be 1–64 simple characters.');
  return {
    schema_version:FIELDDECK_VERSION,
    kind:FIELDDECK_KIND,
    name,
    steps:actionIds.map(action_id=>({
      action_id,timeout_seconds:30,on_failure:'stop',
    })),
    policy:{
      execution:'denied',requires_authentication:true,requires_review:true,
    },
  };
}

export function inspectDraftAndBuild(draft, shelf, actions, name) {
  const inspection=inspectEvieDeckDraft(draft,shelf);
  const blueprint=buildFieldDeckBlueprint(actions,name);
  return {
    inspection, blueprint,
    status:'manual_review_only',
    actionMapping:'not_derived_from_evie_cards',
    executed:false,submitted:false,authorized:false,
    note:'Selected FieldDeck actions are an operator-designed separate plan, not an automated translation.',
  };
}
