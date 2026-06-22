import { describe, it, expect } from 'vitest';
import { listCities, getCityAgenda, getSpeakerSessions, searchSessions, getKeynotes } from '../src/tools';
import type { AgendaData } from '../src/data';

const DATA: AgendaData = {
  generated_at: '2026-06-20T00:00:00Z',
  cities: ['Mexico', 'Chile'],
  sessions: [
    {
      city: 'Mexico', time_slot: null, track: null, is_keynote: true,
      title: 'Keynote MX', speaker_name: 'Eugenio Galiano', speaker_company: 'Oracle',
      speaker_bio: 'AI expert.', oracle_ace: null,
    },
    {
      city: 'Mexico', time_slot: '09:45 – 10:30', track: 'APEX', is_keynote: false,
      title: 'APEX Talk', speaker_name: 'Jayson Hanes', speaker_company: 'Oracle',
      speaker_bio: 'APEX product manager.', oracle_ace: null,
    },
    {
      city: 'Chile', time_slot: null, track: null, is_keynote: true,
      title: 'Keynote CL', speaker_name: 'Eugenio Galiano', speaker_company: 'Oracle',
      speaker_bio: 'AI expert.', oracle_ace: null,
    },
  ],
};

describe('listCities', () => {
  it('returns the cities list', () => {
    expect(listCities(DATA)).toEqual(['Mexico', 'Chile']);
  });
});

describe('getCityAgenda', () => {
  it('returns sessions for a valid city sorted by time slot', () => {
    expect(getCityAgenda(DATA, 'Mexico')).toEqual([DATA.sessions[0], DATA.sessions[1]]);
  });

  it('returns an error with valid cities for an unknown city', () => {
    expect(getCityAgenda(DATA, 'Atlantis')).toEqual({
      error: 'Ciudad no encontrada: Atlantis',
      valid_cities: ['Mexico', 'Chile'],
    });
  });
});

describe('getSpeakerSessions', () => {
  it('finds sessions by exact name across cities', () => {
    expect(getSpeakerSessions(DATA, 'Eugenio Galiano')).toEqual([DATA.sessions[0], DATA.sessions[2]]);
  });

  it('finds sessions by partial, case-insensitive name', () => {
    expect(getSpeakerSessions(DATA, 'galiano')).toHaveLength(2);
  });

  it('returns an empty array for an unknown speaker', () => {
    expect(getSpeakerSessions(DATA, 'Nobody Here')).toEqual([]);
  });
});

describe('searchSessions', () => {
  it('matches by title keyword', () => {
    expect(searchSessions(DATA, 'APEX')).toEqual([DATA.sessions[1]]);
  });

  it('returns an empty array when nothing matches', () => {
    expect(searchSessions(DATA, 'nonexistent-topic')).toEqual([]);
  });
});

describe('getKeynotes', () => {
  it('returns only keynote sessions across all cities', () => {
    expect(getKeynotes(DATA)).toEqual([DATA.sessions[0], DATA.sessions[2]]);
  });
});
