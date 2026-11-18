import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { ThemeToggle } from '../theme/ThemeToggle';

const storageKey = 'nfl-research-sidebar-collapsed';
function savedCollapse() {
  try { return localStorage.getItem(storageKey) === 'true'; } catch { return false; }
}

export function Sidebar({researchPage, schedulePage}: {researchPage:boolean; schedulePage:boolean}) {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(savedCollapse);
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const mobile = () => window.matchMedia?.('(max-width: 760px)').matches;
  const closeMenu = () => {
    setMobileOpen(false);
    if (mobile()) menuButton.current?.focus();
  };
  useEffect(() => { setMobileOpen(false); }, [location.pathname, location.search]);
  useEffect(() => {
    const media = window.matchMedia?.('(max-width: 760px)');
    const reset = () => setMobileOpen(false);
    media?.addEventListener('change', reset);
    return () => media?.removeEventListener('change', reset);
  }, []);
  return <aside className={`sidebar${collapsed?' sidebar-collapsed':''}${mobileOpen?' sidebar-mobile-open':''}`} onKeyDown={event=>{
    if (event.key==='Escape' && mobileOpen) { event.preventDefault(); closeMenu(); }
  }}>
    <Link to="/" className="brand" aria-label="NFL Research home" title="NFL Research home" onClick={closeMenu}><span className="brand-icon">N<span>R</span></span><span className="brand-text">NFL Research<small>THE RESEARCH WORKSPACE</small></span></Link>
    <button className="sidebar-toggle desktop-sidebar-toggle" aria-label={collapsed?'Expand sidebar':'Collapse sidebar'} aria-expanded={!collapsed} aria-controls="workspace-navigation" onClick={()=>{
      setCollapsed(value=>{try { localStorage.setItem(storageKey,String(!value)); } catch { /* In-memory choice remains usable. */ } return !value;});
    }} title={collapsed?'Expand sidebar':'Collapse sidebar'}><span aria-hidden="true">{collapsed?'»':'«'}</span></button>
    <button ref={menuButton} className="sidebar-toggle mobile-sidebar-toggle" aria-label={mobileOpen?'Close navigation':'Open navigation'} aria-expanded={mobileOpen} aria-controls="workspace-navigation" onClick={()=>setMobileOpen(value=>!value)}><span aria-hidden="true">{mobileOpen?'×':'☰'}</span> Menu</button>
    <div className="nav-label">WORKSPACE</div>
    <nav id="workspace-navigation" className="workspace-nav" aria-label="Workspace">
      <Link className="sidebar-link" to="/" aria-current={schedulePage?'page':undefined} aria-label="League schedule" title="League schedule" onClick={closeMenu}><span aria-hidden="true">▦</span><span className="nav-text">League schedule</span></Link>
      <Link className="sidebar-link" to={researchPage?`/rankings${location.search}`:'/rankings'} aria-current={researchPage?'page':undefined} aria-label="Team rankings" title="Team rankings" onClick={closeMenu}><span aria-hidden="true">≡</span><span className="nav-text">Team rankings</span></Link>
      <ThemeToggle />
    </nav>
    <div className="sidebar-bottom"><span className="small-dot"/>Private research workspace<p>Real records. Clear context.</p></div>
  </aside>;
}
