import type { AgendaData, PublicSession } from './data';

export function listCities(data: AgendaData): { city: string; date: string }[] {
  return data.cities.map((city) => ({ city, date: data.city_dates[city] }));
}

export function getCityAgenda(
  data: AgendaData,
  city: string
): PublicSession[] | { error: string; valid_cities: string[] } {
  if (!data.cities.includes(city)) {
    return { error: `Ciudad no encontrada: ${city}`, valid_cities: data.cities };
  }
  return data.sessions
    .filter((s) => s.city === city)
    .sort((a, b) => (a.time_slot ?? '').localeCompare(b.time_slot ?? ''));
}

function normalize(text: string): string {
  return text.trim().toLowerCase();
}

export function getSpeakerSessions(data: AgendaData, speakerName: string): PublicSession[] {
  const needle = normalize(speakerName);
  return data.sessions.filter((s) => normalize(s.speaker_name).includes(needle));
}

export function searchSessions(data: AgendaData, query: string): PublicSession[] {
  const needle = normalize(query);
  return data.sessions.filter(
    (s) =>
      normalize(s.title).includes(needle) ||
      normalize(s.track ?? '').includes(needle) ||
      normalize(s.speaker_bio).includes(needle)
  );
}

export function getKeynotes(data: AgendaData): PublicSession[] {
  return data.sessions.filter((s) => s.is_keynote);
}
