import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
const source=resolve(import.meta.dirname,'../../app/shelf/architecture_cards.json');
const target=resolve(import.meta.dirname,'../src/generated/architecture.json');
const catalog=JSON.parse(readFileSync(source,'utf8'));
if(catalog.schemaVersion!=='evie.shelf.architecture-catalog/1'||!Array.isArray(catalog.cards)||!Array.isArray(catalog.rituals))throw Error('Canonical EVIE Architecture Shelf missing or changed.');
const ids=new Set();for(const c of catalog.cards){if(!c.card_id||!c.slug||ids.has(c.card_id)||!c.execution?.status)throw Error('Invalid or duplicate Shelf record.');ids.add(c.card_id);}
mkdirSync(dirname(target),{recursive:true});writeFileSync(target,JSON.stringify(catalog,null,2)+'\n');
console.log('Synced',catalog.cards.length,'historical cards and',catalog.rituals.length,'rituals from EVIE canonical catalog.');
