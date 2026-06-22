import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchAgendaData, AgendaFetchError } from '../src/data';

const SAMPLE_DATA = {
  generated_at: '2026-06-20T00:00:00Z',
  cities: ['Mexico'],
  sessions: [],
};

function installFakeCache() {
  const store = new Map<string, Response>();
  // @ts-expect-error - simplified Cache mock for tests, real shape not needed
  globalThis.caches = {
    default: {
      async match(req: Request) {
        return store.get(req.url);
      },
      async put(req: Request, res: Response) {
        store.set(req.url, res);
      },
    },
  };
}

describe('fetchAgendaData', () => {
  beforeEach(() => {
    installFakeCache();
  });

  it('returns parsed JSON on a successful fetch', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE_DATA), { status: 200 }));

    const result = await fetchAgendaData('https://example.com/agenda.json');

    expect(result).toEqual(SAMPLE_DATA);
  });

  it('serves the second call from cache without calling fetch again', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(SAMPLE_DATA), { status: 200 }));
    globalThis.fetch = fetchMock;

    await fetchAgendaData('https://example.com/agenda.json');
    await fetchAgendaData('https://example.com/agenda.json');

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws AgendaFetchError when the network request fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down'));

    await expect(fetchAgendaData('https://example.com/agenda.json')).rejects.toThrow(AgendaFetchError);
  });

  it('throws AgendaFetchError on a non-200 response', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('not found', { status: 404 }));

    await expect(fetchAgendaData('https://example.com/agenda.json')).rejects.toThrow(AgendaFetchError);
  });

  it('throws AgendaFetchError when the body is not valid JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('not json', { status: 200 }));

    await expect(fetchAgendaData('https://example.com/agenda.json')).rejects.toThrow(AgendaFetchError);
  });
});
