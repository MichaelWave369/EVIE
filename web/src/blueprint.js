/** Browser-only fixture generator. Never claims to execute a real EVIE job. */
export function createDemoProposal({title='Field Workshop Concept',width=28,depth=20,units='ft',partition='vertical',includeDoor=true,includeNetwork=true}={}){
  if(typeof title!=='string'||!title.trim()||title.length>120)throw Error('Title must be 1–120 characters.');
  if(!['ft','m'].includes(units))throw Error('Units must be ft or m.');
  if(!['none','vertical','horizontal'].includes(partition))throw Error('Invalid partition setting.');
  if(typeof includeDoor!=='boolean'||typeof includeNetwork!=='boolean')throw Error('Invalid marker setting.');
  for(const [label,n] of [['Width',width],['Depth',depth]])if(typeof n!=='number'||!Number.isFinite(n)||n<2||n>100)throw Error(label+' must be between 2 and 100.');
  const w=Number(width.toFixed(6)),d=Number(depth.toFixed(6));
  const thickness=units==='m'?.15:.5,height=units==='m'?2.7:9;
  const wall=(id,x1,y1,x2,y2)=>({id,x1,y1,x2,y2,thickness,height});
  const walls=[wall('demo-n',0,0,w,0),wall('demo-e',w,0,w,d),wall('demo-s',w,d,0,d),wall('demo-w',0,d,0,0)];
  if(partition==='vertical')walls.push(wall('demo-p',w/2,0,w/2,d));
  if(partition==='horizontal')walls.push(wall('demo-p',0,d/2,w,d/2));
  const symbols=[];
  if(includeDoor)symbols.push({id:'demo-door',type:'door',x:w/2,y:d,rotation:0});
  if(includeNetwork)symbols.push({id:'demo-net',type:'network',x:Number((w*.75).toFixed(6)),y:Number((d*.75).toFixed(6)),rotation:0});
  return {schemaVersion:'openblueprint.evie-proposal/1',
    source:{system:'EVIE',cardId:'public_porch_demo',runId:'browser-fixture-not-a-run',mode:'fixture'},
    project:{schemaVersion:'openblueprint.project/1',metadata:{title:title.trim(),units,grid:units==='m'?.25:1,updatedAt:new Date().toISOString()},walls,symbols}};
}
export function saveProposal(proposal){
  const blob=new Blob([JSON.stringify(proposal,null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='evie-commons-demo.proposal.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),0);
}
