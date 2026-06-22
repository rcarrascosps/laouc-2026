import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { WebStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import { z } from 'zod';
import { fetchAgendaData, AgendaFetchError } from './data';
import { listCities, getCityAgenda, getSpeakerSessions, searchSessions, getKeynotes } from './tools';

export interface Env {
  AGENDA_JSON_URL: string;
}

function buildServer(env: Env): McpServer {
  const server = new McpServer({ name: 'laouc-agenda', version: '1.0.0' });

  server.tool('list_cities', 'Lista las 9 ciudades del LAOUC Tour 2026', {}, async () => {
    const data = await fetchAgendaData(env.AGENDA_JSON_URL);
    return { content: [{ type: 'text', text: JSON.stringify(listCities(data)) }] };
  });

  server.tool(
    'get_city_agenda',
    'Devuelve la agenda completa de una ciudad del tour, ordenada por horario',
    { city: z.string().describe('Nombre exacto de la ciudad, ej. "Mexico"') },
    async ({ city }: { city: string }) => {
      const data = await fetchAgendaData(env.AGENDA_JSON_URL);
      return { content: [{ type: 'text', text: JSON.stringify(getCityAgenda(data, city)) }] };
    }
  );

  server.tool(
    'get_speaker_sessions',
    'Devuelve todas las sesiones confirmadas de un speaker en cualquier ciudad del tour',
    { speaker_name: z.string().describe('Nombre completo o parcial del speaker') },
    async ({ speaker_name }: { speaker_name: string }) => {
      const data = await fetchAgendaData(env.AGENDA_JSON_URL);
      const sessions = getSpeakerSessions(data, speaker_name);
      const text = sessions.length
        ? JSON.stringify(sessions)
        : `No encontré sesiones para "${speaker_name}". Revisa la ortografía del nombre.`;
      return { content: [{ type: 'text', text }] };
    }
  );

  server.tool(
    'search_sessions',
    'Busca sesiones por palabra clave en el título, track o biografía del speaker',
    { query: z.string().describe('Palabra clave a buscar, ej. "AI" o "GoldenGate"') },
    async ({ query }: { query: string }) => {
      const data = await fetchAgendaData(env.AGENDA_JSON_URL);
      const sessions = searchSessions(data, query);
      const text = sessions.length
        ? JSON.stringify(sessions)
        : `No encontré sesiones que coincidan con "${query}".`;
      return { content: [{ type: 'text', text }] };
    }
  );

  server.tool('get_keynotes', 'Lista los keynotes confirmados de las 9 ciudades del tour', {}, async () => {
    const data = await fetchAgendaData(env.AGENDA_JSON_URL);
    return { content: [{ type: 'text', text: JSON.stringify(getKeynotes(data)) }] };
  });

  return server;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      const server = buildServer(env);
      const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      await server.connect(transport);
      return await transport.handleRequest(request);
    } catch (err) {
      if (err instanceof AgendaFetchError) {
        return new Response(
          JSON.stringify({ error: `La agenda no está disponible en este momento: ${err.message}` }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
      }
      return new Response(JSON.stringify({ error: 'Error interno del servidor.' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};
