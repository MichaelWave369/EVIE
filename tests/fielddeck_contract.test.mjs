/** Pinned source-to-source contract, exercising FieldDeck's actual parser. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  buildFieldDeckBlueprint,inspectEvieDeckDraft,inspectDraftAndBuild
} from '../web/src/fielddeckBridge.js';

const dir=process.env.FIELDDECK_CHECKOUT;
const expected=process.env.FIELDDECK_REVISION;
if (process.env.CI && (!dir || !expected))
  throw Error('Cross-repo CI needs a pinned FieldDeck checkout.');
const available=Boolean(dir && expected);

async function recipient(){
  const folder=resolve(dir);
  const head=execFileSync('git',['-C',folder,'rev-parse','HEAD'],{encoding:'utf8',timeout:5000}).trim();
  assert.match(expected,/^[a-f0-9]{40}$/);
  assert.equal(head,expected,'FieldDeck checkout must match explicit pinned revision');
  const changed=execFileSync('git',['-C',folder,'status','--porcelain','--',
    'src/blueprint-model.mjs','src/chain-model.mjs','package.json'],
    {encoding:'utf8',timeout:5000}).trim();
  assert.equal(changed,'','Do not test dirty recipient parser source');
  return import(pathToFileURL(join(folder,'src/blueprint-model.mjs')).href);
}

test('EVIE design card IDs never become recipient action IDs',()=>{
  const shelf={cards:[{id:'EVIE-A',name:'Original Shelf Card A',status:'catalog_only'},
    {id:'EVIE-B',name:'Original Shelf Card B',status:'catalog_only'}]};
  const draft={schemaVersion:'evie.deck.draft/1',origin:'EVIE Commons public static Shelf',mode:'design-only',
    createdAt:'2026-10-09T00:00:00Z',
    cards:[{position:0,cardId:'EVIE-A'},{position:1,cardId:'EVIE-B'}],
    validation:{unresolvedSteps:1,unverifiedSteps:2,executable:false},
    note:'Design-only draft.'};
  const review=inspectEvieDeckDraft(JSON.stringify(draft),shelf);
  assert.equal(review.count,2);
  assert.equal(review.importedAsFieldDeckActions,0);
  const planned=inspectDraftAndBuild(JSON.stringify(draft),shelf,['catalog-health'],'EVIE Review Draft');
  assert.equal(planned.actionMapping,'not_derived_from_evie_cards');
  assert.equal(planned.executed,false);
  assert.equal(planned.blueprint.policy.execution,'denied');
  assert.throws(()=>buildFieldDeckBlueprint(['EVIE-A']),/reviewed action/);
});

test('actual FieldDeck parser accepts manually selected, default-deny EVIE blueprint', {skip:!available}, async()=>{
  const fd=await recipient();
  const plan=buildFieldDeckBlueprint(['catalog-health','script-smoke'],'EVIE Review Draft');
  assert.deepEqual(plan,fd.createBlueprint(['catalog-health','script-smoke'],'EVIE Review Draft'));
  const parsed=fd.parseBlueprint(JSON.stringify(plan));
  assert.deepEqual(parsed,{name:'EVIE Review Draft',steps:['catalog-health','script-smoke'],imported:true});
  const preflight=fd.preflightChain(parsed.steps);
  assert.equal(preflight.execution_authorized,false);
  assert.equal(preflight.is_execution_receipt,false);
});

test('three reviewed actions never imply execution, even if arranged as approved preset', {skip:!available}, async()=>{
  const fd=await recipient();
  const plan=buildFieldDeckBlueprint(['catalog-health','script-smoke','macro-demo'],'EVIE Review Draft');
  const parsed=fd.parseBlueprint(JSON.stringify(plan));
  const preflight=fd.preflightChain(parsed.steps);
  assert.equal(preflight.execution_authorized,false);
  assert.equal(preflight.requires_authenticated_github_submission,true);
  assert.equal(plan.policy.execution,'denied');
});

test('actual FieldDeck parser rejects forged permissions, unknown actions and arbitrary fields', {skip:!available}, async()=>{
  const fd=await recipient();
  const plan=buildFieldDeckBlueprint(['catalog-health'],'EVIE Review Draft');
  const changed=[
    {...plan,policy:{...plan.policy,execution:'allowed'}},
    {...plan,steps:[{...plan.steps[0],action_id:'evie-shelf-undefined'}]},
    {...plan,extra:'execution'},
    {...plan,steps:[{...plan.steps[0],on_failure:'continue'}]},
  ];
  for(const record of changed)assert.throws(()=>fd.parseBlueprint(JSON.stringify(record)));
});

test('pinned recipient parser is exactly the examined FieldDeck revision', {skip:!available}, async()=>{
  const fd=await recipient();
  assert.equal(fd.BLUEPRINT_VERSION,'0.5.0');
  assert.equal(fd.MAX_BLUEPRINT_BYTES,16384);
});
