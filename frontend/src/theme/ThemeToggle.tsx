import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';
const key = 'nfl-research-theme';
const valid = (value: string | null): Theme => value === 'light' || value === 'dark' ? value : 'system';
function stored(): Theme {
  try { return valid(localStorage.getItem(key)); } catch { return 'system'; }
}

/** The head script handles first paint; this control handles interactive changes. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(stored);
  useEffect(() => {
    const media = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    const apply = () => {
      const dark = theme === 'dark' || (theme === 'system' && !!media?.matches);
      document.documentElement.classList.toggle('dark', dark);
      document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
    };
    apply();
    media?.addEventListener('change', apply);
    return () => media?.removeEventListener('change', apply);
  }, [theme]);
  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === key || event.key === null) setTheme(stored());
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);
  return <div className="theme-control"><label htmlFor="theme-preference">Theme</label>
    <select id="theme-preference" title={`Theme: ${theme}`} value={theme} onChange={event => {
      const next = valid(event.target.value);
      setTheme(next);
      try { localStorage.setItem(key, next); } catch { /* Keep the in-memory choice usable. */ }
    }}>
      <option value="light">Light</option><option value="dark">Dark</option><option value="system">System</option>
    </select>
  </div>;
}
