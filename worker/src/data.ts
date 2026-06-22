export interface PublicSession {
  city: string;
  time_slot: string | null;
  track: string | null;
  is_keynote: boolean;
  title: string;
  speaker_name: string;
  speaker_company: string;
  speaker_bio: string;
  oracle_ace: string | null;
}

export interface AgendaData {
  generated_at: string;
  cities: string[];
  sessions: PublicSession[];
}

export class AgendaFetchError extends Error {}

const CACHE_KEY = 'https://laouc-agenda-mcp.internal/agenda-cache';
const CACHE_TTL_SECONDS = 300;

export async function fetchAgendaData(agendaJsonUrl: string): Promise<AgendaData> {
  const cache = caches.default;
  const cacheRequest = new Request(CACHE_KEY);

  try {
    const cached = await cache.match(cacheRequest);
    if (cached) {
      return (await cached.json()) as AgendaData;
    }
  } catch {
    // Treat a broken cache read as a cache miss — fall through to the network fetch below.
  }

  let response: Response;
  try {
    response = await fetch(agendaJsonUrl);
  } catch (err) {
    throw new AgendaFetchError(`No se pudo contactar a GitHub: ${(err as Error).message}`);
  }

  if (!response.ok) {
    throw new AgendaFetchError(`GitHub respondió con estado ${response.status}`);
  }

  let data: AgendaData;
  try {
    data = (await response.json()) as AgendaData;
  } catch (err) {
    throw new AgendaFetchError('El JSON de la agenda está mal formado.');
  }

  const cacheResponse = new Response(JSON.stringify(data), {
    headers: { 'Cache-Control': `max-age=${CACHE_TTL_SECONDS}` },
  });
  await cache.put(cacheRequest, cacheResponse);

  return data;
}
