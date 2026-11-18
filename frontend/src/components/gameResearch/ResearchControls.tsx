import { useState } from 'react';
import { canonicalLine } from '../../api/gameResearch';
import type { ResearchWindow } from '../../api/gameResearch';

export const researchWindows: Record<ResearchWindow,string> = {L3:'Last 3 Games',L5:'Last 5 Games',L10:'Last 10 Games',L20:'Last 20 Games',SEASON:'Selected Season',H2H:'Head to Head'};
export function RecentGamesSelector({value,onChange}: {value:ResearchWindow;onChange:(value:ResearchWindow)=>void}) {
  return <div className="season-control"><label htmlFor="game-research-window">Research window</label><select id="game-research-window" value={value} onChange={event=>onChange(event.target.value as ResearchWindow)}>
    {Object.entries(researchWindows).map(([key,label])=><option value={key} key={key}>{key} — {label}</option>)}
  </select></div>;
}
export function BettingLineControl({line,onChange}: {line:string|null;onChange:(value:string|null)=>void}) {
  const [draft,setDraft]=useState(line ?? '');
  const parsed=canonicalLine(draft);
  const change=(value:string|null)=>{setDraft(value ?? '');onChange(value);};
  const step=(delta:number)=>{
    if (parsed === undefined || parsed === null) return;
    change(canonicalLine((Number(parsed)+delta).toFixed(6))!);
  };
  return <form className="research-line-control" onSubmit={event=>{event.preventDefault();if(parsed!==undefined) onChange(parsed);}}>
    <label htmlFor="game-research-line">Custom Game Total line</label>
    <div className="research-line-actions">
      <button type="button" className="button secondary" aria-label="Decrease Game Total line by 0.5" disabled={parsed==null || Number(parsed)<0.5} onClick={()=>step(-0.5)}>− 0.5</button>
      <input id="game-research-line" type="number" inputMode="decimal" min="0" max="1000000" step="any" value={draft} placeholder="Enter a line" aria-describedby="game-research-line-help" aria-invalid={parsed===undefined} onChange={event=>setDraft(event.target.value)}/>
      <button type="button" className="button secondary" aria-label="Increase Game Total line by 0.5" disabled={parsed==null || Number(parsed)>999999.5} onClick={()=>step(0.5)}>+ 0.5</button>
      <button type="submit" className="button" disabled={parsed===undefined}>Apply line</button>
      <button type="button" className="button secondary" onClick={()=>change(null)}>Clear line</button>
    </div>
    <p id="game-research-line-help">Manual research threshold only; historical reference totals are unchanged.</p>
    {parsed===undefined ? <p role="alert">Enter a line from 0 to 1,000,000 with up to six decimal places.</p> : parsed!==line && <p role="status">Apply the edited line to update results. Displayed results use {line ?? 'no custom line'}.</p>}
  </form>;
}
