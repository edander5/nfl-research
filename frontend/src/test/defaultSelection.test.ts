import { describe, expect, it } from 'vitest';
import type { Game, Round } from '../api/types';
import { defaultSelection, easternDay } from '../schedule/defaultSelection';
import { game, seasons } from './fixtures';

const fixture = (season: number, week: number, date: string | null, round?: Round) => game({
  season, week, season_type: round ? 'POST' : 'REG', game_type: round ?? 'REG',
  scheduled_kickoff_utc: date, source_gameday: null,
});
const calendar = [
  fixture(2026, 8, '2026-10-29T00:15:00Z'),
  fixture(2026, 8, '2026-11-03T01:15:00Z'),
  fixture(2026, 9, '2026-11-06T01:15:00Z'),
  fixture(2026, 9, '2026-11-10T01:15:00Z'),
  fixture(2026, 10, '2026-11-13T01:15:00Z'),
  fixture(2026, 10, '2026-11-17T01:15:00Z'),
];
const choose = (records: Game[], now: string) => defaultSelection(records, seasons.data, new Date(now));

describe('date-driven home selection', () => {
  it('selects the active regular-season span through its Monday', () => {
    expect(choose(calendar, '2026-11-09T17:00:00Z')).toMatchObject({season:2026,stage:'REG',selection:'9',reason:'active'});
  });
  it('moves to the next actual week during a gap after Monday', () => {
    expect(choose(calendar, '2026-11-11T17:00:00Z')).toMatchObject({selection:'10',reason:'upcoming'});
  });
  it('uses actual irregular dates, not opener plus seven-day arithmetic', () => {
    const irregular = [fixture(2026,1,'2026-09-10T20:00:00Z'),fixture(2026,2,'2026-09-23T20:00:00Z')];
    expect(choose(irregular,'2026-09-20T12:00:00Z')).toMatchObject({selection:'2',reason:'upcoming'});
  });
  it('prefers a newer active week over an old postponed span', () => {
    const overlapping = [...calendar,fixture(2026,8,'2026-11-15T18:00:00Z')];
    expect(choose(overlapping,'2026-11-09T17:00:00Z')).toMatchObject({selection:'9'});
    expect(choose(overlapping,'2026-11-11T17:00:00Z')).toMatchObject({selection:'10'});
  });
  it('uses January fixtures original NFL season, not calendar year', () => {
    const records = [fixture(2026,18,'2027-01-10T18:00:00Z'),fixture(2026,19,'2027-01-16T18:00:00Z','WC')];
    expect(choose(records,'2027-01-10T23:00:00Z')).toMatchObject({season:2026,stage:'REG',selection:'18'});
    expect(choose(records,'2027-01-11T17:00:00Z')).toMatchObject({season:2026,stage:'POST',selection:'WC'});
  });
  it('selects a current postseason round and then its next available round', () => {
    const records = [fixture(2026,19,'2027-01-16T18:00:00Z','WC'),fixture(2026,19,'2027-01-19T01:00:00Z','WC'),fixture(2026,20,'2027-01-23T18:00:00Z','DIV')];
    expect(choose(records,'2027-01-18T17:00:00Z')).toMatchObject({stage:'POST',selection:'WC'});
    expect(choose(records,'2027-01-20T17:00:00Z')).toMatchObject({stage:'POST',selection:'DIV'});
  });
  it('offseason selects the next published opener, even if an older season is available', () => {
    const records = [fixture(2025,22,'2026-02-08T23:30:00Z','SB'),fixture(2026,1,'2026-09-10T20:00:00Z')];
    expect(choose(records,'2026-07-01T12:00:00Z')).toMatchObject({season:2026,stage:'REG',selection:'1',reason:'upcoming'});
  });
  it('after the available season ends retains the most recent available round', () => {
    expect(choose([fixture(2026,22,'2027-02-07T23:30:00Z','SB')],'2027-06-01T12:00:00Z')).toMatchObject({season:2026,stage:'POST',selection:'SB',reason:'latest'});
  });
  it('uses known source Eastern date when kickoff time is missing', () => {
    const records = [game({week:9,scheduled_kickoff_utc:null,source_gameday:'2026-11-09'}),fixture(2026,10,'2026-11-13T01:15:00Z')];
    expect(choose(records,'2026-11-09T17:00:00Z')).toMatchObject({selection:'9',reason:'active'});
  });
  it('uses available coverage when every date or game response is missing', () => {
    expect(choose([game({week:9,scheduled_kickoff_utc:null,source_gameday:null})],'2026-11-09T17:00:00Z')).toMatchObject({selection:'9',reason:'undated'});
    expect(choose([],'2026-11-09T17:00:00Z')).toMatchObject({season:2026,selection:'1',reason:'undated'});
    expect(defaultSelection([],[],new Date('2026-11-09T17:00:00Z'))).toBeNull();
  });
  it('ignores invalid dates rather than deriving a fictitious kickoff', () => {
    expect(choose([game({scheduled_kickoff_utc:'invalid',source_gameday:'2026-02-30'})],'2026-11-09T17:00:00Z')).toMatchObject({reason:'undated'});
  });
  it('never uses score/finality to choose a week and never mutates records', () => {
    const before = JSON.stringify(calendar);
    choose(calendar,'2026-11-09T17:00:00Z');
    expect(JSON.stringify(calendar)).toBe(before);
    expect(choose(calendar.map(g => ({...g,status:'FINAL' as const,reported_home_score:99})),'2026-11-09T17:00:00Z')).toEqual(choose(calendar,'2026-11-09T17:00:00Z'));
  });
});

describe('Eastern calendar boundaries', () => {
  it.each([
    ['2026-11-10T04:59:59Z','9'], ['2026-11-10T05:00:00Z','10'],
    ['2026-11-10T13:59:59+09:00','9'], ['2026-11-09T21:00:00-08:00','10'],
  ])('selects by Eastern day for %s', (now,week) => expect(choose(calendar,now)?.selection).toBe(week));
  it('uses EDT boundaries as well as EST', () => {
    const records = [fixture(2026,1,'2026-09-15T00:15:00Z'),fixture(2026,2,'2026-09-18T00:15:00Z')];
    expect(choose(records,'2026-09-15T03:59:59Z')?.selection).toBe('1');
    expect(choose(records,'2026-09-15T04:00:00Z')?.selection).toBe('2');
  });
  it('keeps the same Eastern day on both sides of the DST fallback hour', () => {
    expect(easternDay(new Date('2026-11-01T05:30:00Z'))).toBe('2026-11-01');
    expect(easternDay(new Date('2026-11-01T06:30:00Z'))).toBe('2026-11-01');
  });
});
