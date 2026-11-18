import { readFileSync } from 'node:fs';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter, useLocation } from 'react-router';
import { Sidebar } from '../components/Sidebar';

const key='nfl-research-sidebar-collapsed';
let mobile=false;
let resize:()=>void;
function Shell(){const location=useLocation();return <><Sidebar researchPage={location.pathname.startsWith('/rankings')} schedulePage={!location.pathname.startsWith('/rankings')}/><output>{location.pathname}</output></>;}
function open(path='/'){return render(<MemoryRouter initialEntries={[path]}><Shell/></MemoryRouter>);}
beforeEach(()=>{
  localStorage.clear();mobile=false;
  vi.stubGlobal('matchMedia',vi.fn((query:string)=>({matches:query.includes('max-width')?mobile:false,addEventListener:(_event:string,callback:()=>void)=>{if(query.includes('max-width'))resize=callback;},removeEventListener:vi.fn()})));
});
afterEach(()=>{localStorage.clear();vi.restoreAllMocks();document.documentElement.classList.remove('dark');});
it('collapses, persists across remount, and expands with accessible native buttons',()=>{
  const view=open();const toggle=screen.getByRole('button',{name:'Collapse sidebar'});
  expect(toggle).toHaveAttribute('aria-expanded','true');toggle.focus();expect(toggle).toHaveFocus();
  fireEvent.click(toggle);expect(screen.getByRole('button',{name:'Expand sidebar'})).toHaveAttribute('aria-expanded','false');
  expect(document.querySelector('aside')).toHaveClass('sidebar-collapsed');expect(localStorage.getItem(key)).toBe('true');
  view.unmount();open();fireEvent.click(screen.getByRole('button',{name:'Expand sidebar'}));expect(localStorage.getItem(key)).toBe('false');
});
it.each([false,true])('preserves navigation and theme controls (collapsed=%s)',collapsed=>{
  localStorage.setItem(key,String(collapsed));open('/games/example');
  const schedule=screen.getByRole('link',{name:'League schedule'});expect(schedule).toHaveAttribute('aria-current','page');expect(schedule).toHaveAttribute('title','League schedule');
  fireEvent.click(screen.getByRole('link',{name:'Team rankings'}));expect(screen.getByRole('status')).toHaveTextContent('/rankings');
  expect(screen.getByRole('link',{name:'Team rankings'})).toHaveAttribute('aria-current','page');
  for(const theme of ['dark','light','system']){fireEvent.change(screen.getByLabelText('Theme'),{target:{value:theme}});expect(screen.getByLabelText('Theme')).toHaveValue(theme);expect(localStorage.getItem('nfl-research-theme')).toBe(theme);}
  fireEvent.click(schedule);expect(screen.getByRole('status')).toHaveTextContent('/');
});
it('uses an independent closed mobile disclosure; Escape and navigation restore focus',()=>{
  mobile=true;localStorage.setItem(key,'true');open();
  const button=screen.getByRole('button',{name:'Open navigation'});expect(button).toHaveAttribute('aria-expanded','false');
  fireEvent.click(button);expect(button).toHaveAttribute('aria-expanded','true');
  screen.getByRole('link',{name:'Team rankings'}).focus();fireEvent.keyDown(document.activeElement!,{key:'Escape'});
  expect(button).toHaveFocus();expect(button).toHaveAttribute('aria-expanded','false');
  fireEvent.click(button);fireEvent.click(screen.getByRole('link',{name:'Team rankings'}));expect(button).toHaveFocus();expect(button).toHaveAttribute('aria-expanded','false');expect(localStorage.getItem(key)).toBe('true');
  fireEvent.click(button);act(()=>resize());expect(button).toHaveAttribute('aria-expanded','false');
});
it('remains usable when storage is blocked or contains an invalid value',()=>{
  localStorage.setItem(key,'invalid');const view=open();expect(screen.getByRole('button',{name:'Collapse sidebar'})).toBeInTheDocument();view.unmount();
  vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw Error('blocked');});vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('blocked');});
  open();fireEvent.click(screen.getByRole('button',{name:'Collapse sidebar'}));expect(screen.getByRole('button',{name:'Expand sidebar'})).toBeInTheDocument();
});
it('defines responsive visibility, main-column expansion and visible keyboard focus',()=>{
  const css=readFileSync('src/styles.css','utf8');
  expect(css).toContain('.app-shell:has(.sidebar-collapsed) { grid-template-columns:80px minmax(0,1fr); }');
  expect(css).toContain('.sidebar .workspace-nav { display:none;');expect(css).toContain('.sidebar-mobile-open .workspace-nav { display:flex; }');
  expect(css).toContain('.sidebar :focus-visible { outline:3px solid');
});
