import { describe, expect, it } from 'vitest';
import shelf from './generated/nested-shelf.json';
import {
  inspectEvieDeckDraft, buildFieldDeckBlueprint, inspectDraftAndBuild,
  FIELDDECK_ACTIONS
} from './fielddeckBridge.js';
import { makeDeckDraft } from './nestedLogic.js';

const draft=()=>makeDeckDraft(shelf.cards.slice(0,3).map(c=>c.id),shelf);

describe('EVIE → FieldDeck manually composed blueprint',()=>{
  it('inspects actual sovereign shelf draft without automatically mapping cards',()=>{
    const r=inspectEvieDeckDraft(JSON.stringify(draft()),shelf);
    expect(r.count).toBe(3);
    expect(r.executable).toBe(false);
    expect(r.importedAsFieldDeckActions).toBe(0);
  });
  it('builds a recipient-shaped, denied blueprint only from explicit reviewed action selections',()=>{
    const plan=inspectDraftAndBuild(JSON.stringify(draft()),shelf,
      ['catalog-health','script-smoke'],'EVIE Review Draft');
    expect(plan.status).toBe('manual_review_only');
    expect(plan.actionMapping).toBe('not_derived_from_evie_cards');
    expect(plan.executed).toBe(false);
    expect(plan.authorized).toBe(false);
    expect(plan.blueprint).toEqual({
      schema_version:'0.5.0',kind:'fielddeck.chain.blueprint',name:'EVIE Review Draft',
      steps:[
        {action_id:'catalog-health',timeout_seconds:30,on_failure:'stop'},
        {action_id:'script-smoke',timeout_seconds:30,on_failure:'stop'},
      ],
      policy:{execution:'denied',requires_authentication:true,requires_review:true},
    });
  });
  it('rejects an arbitrary EVIE card passed as FieldDeck action',()=>{
    expect(()=>buildFieldDeckBlueprint([shelf.cards[0].id])).toThrow('reviewed action');
    expect(()=>buildFieldDeckBlueprint(['rm -rf /'])).toThrow('reviewed action');
    expect(()=>buildFieldDeckBlueprint(Array(7).fill('script-smoke'))).toThrow('1–6');
    expect(()=>buildFieldDeckBlueprint(['catalog-health'], ' injected\nscript')).toThrow('Name');
    expect(FIELDDECK_ACTIONS).toHaveLength(3);
  });
  it('rejects fabricated authority, invented cards and reordered IDs',()=>{
    const baseline=draft();
    for(const bad of [
      {...baseline,mode:'execute'},
      {...baseline,validation:{...baseline.validation,executable:true}},
      {...baseline,cards:[{position:0,cardId:'unknown'}]},
      {...baseline,cards:[{position:1,cardId:shelf.cards[0].id}]},
      {...baseline,cards:[{position:0,cardId:shelf.cards[0].id},{position:1,cardId:shelf.cards[0].id}]},
      {...baseline,actionAuthorized:true},
    ])expect(()=>inspectEvieDeckDraft(bad,shelf)).toThrow();
  });
});
