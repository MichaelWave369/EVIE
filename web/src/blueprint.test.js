import{describe,it,expect}from'vitest';import{createDemoProposal}from'./blueprint.js';
describe('EVIE public demo blueprint contract',()=>{
 it('generates only a marked fixture-compatible import',()=>{const p=createDemoProposal({width:16,depth:10,partition:'horizontal'});expect(p.schemaVersion).toBe('openblueprint.evie-proposal/1');expect(p.source.mode).toBe('fixture');expect(p.source.runId).toContain('not-a-run');expect(p.project.schemaVersion).toBe('openblueprint.project/1');expect(p.project.walls).toHaveLength(5);expect(p.project.symbols).toHaveLength(2);});
 it('supports metric units and no markers',()=>{const p=createDemoProposal({units:'m',partition:'none',includeDoor:false,includeNetwork:false});expect(p.project.metadata.units).toBe('m');expect(p.project.walls[0].height).toBe(2.7);expect(p.project.walls).toHaveLength(4);expect(p.project.symbols).toHaveLength(0);});
 it.each([{width:0},{depth:Infinity},{width:NaN},{units:'in'},{partition:'other'},{title:''},{includeDoor:'yes'}])('rejects invalid constraints %s',opts=>expect(()=>createDemoProposal(opts)).toThrow());
});
