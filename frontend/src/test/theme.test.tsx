import { readFileSync } from 'node:fs';
import { fireEvent, render, screen, act, within } from '@testing-library/react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { App } from '../App';
import { ThemeToggle } from '../theme/ThemeToggle';

const key = 'nfl-research-theme';
const bootstrap = readFileSync('public/theme.js', 'utf8');
const html = readFileSync('index.html', 'utf8');
const css = readFileSync('src/styles.css', 'utf8');
let media: { matches: boolean; addEventListener: ReturnType<typeof vi.fn>; removeEventListener: ReturnType<typeof vi.fn> };
beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove('dark');
  document.documentElement.style.colorScheme = '';
  media = { matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() };
  vi.stubGlobal('matchMedia', vi.fn(() => media));
});
afterEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove('dark');
  document.documentElement.style.colorScheme = '';
});
const startup = () => window.eval(bootstrap);
const control = () => screen.getByRole('combobox', { name: 'Theme' });
const choose = (value: string) => fireEvent.change(control(), { target: { value } });

it.each([true, false])('defaults to system preference at startup and mount (dark=%s)', dark => {
  media.matches = dark;
  startup();
  expect(document.documentElement.classList.contains('dark')).toBe(dark);
  render(<ThemeToggle />);
  expect(control()).toHaveValue('system');
  expect(document.documentElement.style.colorScheme).toBe(dark ? 'dark' : 'light');
  expect(localStorage.getItem(key)).toBeNull();
});

it.each(['light', 'dark', 'system'])('persists %s across remount and startup', value => {
  const view = render(<ThemeToggle />);
  choose(value);
  expect(localStorage.getItem(key)).toBe(value);
  expect(document.documentElement.classList.contains('dark')).toBe(value !== 'light');
  view.unmount();
  document.documentElement.classList.remove('dark');
  startup();
  expect(document.documentElement.classList.contains('dark')).toBe(value !== 'light');
  render(<ThemeToggle />);
  expect(control()).toHaveValue(value);
});

it('follows changing system preferences only in System mode and cleans listeners', () => {
  const view = render(<ThemeToggle />);
  act(() => { media.matches = false; media.addEventListener.mock.calls.at(-1)![1](); });
  expect(document.documentElement).not.toHaveClass('dark');
  choose('dark');
  act(() => { media.addEventListener.mock.calls.at(-1)![1](); });
  expect(document.documentElement).toHaveClass('dark');
  choose('light');
  act(() => { media.matches = true; media.addEventListener.mock.calls.at(-1)![1](); });
  expect(document.documentElement).not.toHaveClass('dark');
  choose('system');
  expect(document.documentElement).toHaveClass('dark');
  view.unmount();
  expect(media.removeEventListener).toHaveBeenCalledTimes(media.addEventListener.mock.calls.length);
});

it('handles invalid saved settings and blocked storage', () => {
  localStorage.setItem(key, 'invalid');
  startup();
  const view = render(<ThemeToggle />);
  expect(control()).toHaveValue('system');
  view.unmount();
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
  expect(startup).not.toThrow();
  render(<ThemeToggle />);
  choose('light');
  expect(control()).toHaveValue('light');
  expect(document.documentElement).not.toHaveClass('dark');
});

it('syncs saved preferences and resets from another tab', () => {
  render(<ThemeToggle />);
  localStorage.setItem(key, 'light');
  act(() => { window.dispatchEvent(new StorageEvent('storage', { key })); });
  expect(control()).toHaveValue('light');
  expect(document.documentElement).not.toHaveClass('dark');
  localStorage.clear();
  act(() => { window.dispatchEvent(new StorageEvent('storage', { key: null })); });
  expect(control()).toHaveValue('system');
  expect(document.documentElement).toHaveClass('dark');
});

it('falls back to light without matchMedia and still supports explicit dark', () => {
  vi.stubGlobal('matchMedia', undefined);
  expect(startup).not.toThrow();
  render(<ThemeToggle />);
  expect(document.documentElement).not.toHaveClass('dark');
  choose('dark');
  expect(document.documentElement).toHaveClass('dark');
});

it('loads the blocking first-paint script in the head before the app', () => {
  expect(html.indexOf('<script src="/theme.js"></script>')).toBeLessThan(html.indexOf('</head>'));
  expect(html.indexOf('/theme.js')).toBeLessThan(html.indexOf('/src/main.tsx'));
  expect(html).not.toMatch(/(?:defer|async)[^>]*src="\/theme.js"/);
});

it('keeps rank colors readable on both theme surfaces', () => {
  const luminance = (hex: string) => {
    const values = hex.slice(1).match(/../g)!.map(part => {
      const s = parseInt(part, 16) / 255;
      return s <= .04045 ? s / 12.92 : ((s + .055) / 1.055) ** 2.4;
    });
    return values[0] * .2126 + values[1] * .7152 + values[2] * .0722;
  };
  for (const selector of [':root {', ':root.dark {']) {
    const block = css.slice(css.indexOf(selector)).split('}')[0];
    const token = (name: string) => block.match(new RegExp(`--${name}:\\s*(#[a-f0-9]+)`))![1];
    for (const foreground of ['positive', 'negative', 'neutral']) {
      for (const background of ['card', 'muted']) {
        const expand = (hex: string) => hex.length === 4 ? '#' + [...hex.slice(1)].map(c => c + c).join('') : hex;
        const a = luminance(expand(token(foreground))), b = luminance(expand(token(background)));
        expect((Math.max(a, b) + .05) / (Math.min(a, b) + .05)).toBeGreaterThanOrEqual(4.5);
      }
    }
  }
});


it('exposes the labeled theme selector in the main navigation', () => {
  render(<MemoryRouter initialEntries={['/unknown-page']}><App /></MemoryRouter>);
  const nav = screen.getByRole('navigation', { name: 'Workspace' });
  expect(within(nav).getByRole('combobox', { name: 'Theme' })).toHaveValue('system');
  expect(within(nav).getAllByRole('option').map(option => option.textContent)).toEqual(['Light', 'Dark', 'System']);
  choose('dark');
  expect(document.documentElement).toHaveClass('dark');
  expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument();
});

it('honors saved dark preference before mount even when the system is light', () => {
  media.matches = false;
  localStorage.setItem(key, 'dark');
  startup();
  expect(document.documentElement).toHaveClass('dark');
  render(<ThemeToggle />);
  expect(control()).toHaveValue('dark');
  expect(document.documentElement.style.colorScheme).toBe('dark');
});
