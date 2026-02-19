import { ROUTES } from './generated/routes'

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '') || '/api';

type PageMeta = {
  limit: number;
  has_more: boolean;
  next_cursor: string | null;
};

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail ?? err));
  }
  if (res.headers.get('content-type')?.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  return res.blob() as unknown as Promise<T>;
}

function withQuery(path: string, params: Record<string, string | number | boolean | undefined | null>): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue;
    qs.set(key, String(value));
  }
  const suffix = qs.toString();
  if (!suffix) return path;
  return `${path}${path.includes('?') ? '&' : '?'}${suffix}`;
}

function fillRoute(template: string, params: Record<string, string>): string {
  return Object.entries(params).reduce(
    (out, [key, value]) => out.replaceAll(`{${key}}`, encodeURIComponent(value)),
    template
  );
}

export const api = {
  health: () => request<{ status: string }>(ROUTES.health_health_get),
  listInvestigations: async () => {
    const investigations: Array<{
      investigation_uid: string;
      title: string;
      description?: string;
      is_archived: boolean;
      current_tier: string;
    }> = [];
    let cursor: string | null = null;
    for (let i = 0; i < 50; i += 1) {
      const resp = await request<{
        investigations: Array<{
          investigation_uid: string;
          title: string;
          description?: string;
          is_archived: boolean;
          current_tier: string;
        }>;
        page?: PageMeta;
      }>(withQuery(ROUTES.list_investigations_investigations_get, { cursor }));
      investigations.push(...resp.investigations);
      cursor = resp.page?.next_cursor ?? null;
      if (!cursor) break;
    }
    return { investigations };
  },
  getInvestigation: (id: string) =>
    request<{
      investigation_uid: string;
      title: string;
      description?: string;
      is_archived: boolean;
      current_tier: string;
      tier_changed_at?: string;
      created_at: string;
      updated_at?: string;
    }>(fillRoute(ROUTES.get_investigation_investigations__investigation_uid__get, { investigation_uid: id })),
  createInvestigation: (body: { title: string; description?: string; investigation_key?: string }) =>
    request<{ event_id: string; investigation_uid: string }>(ROUTES.create_investigation_investigations_post, { method: 'POST', body: JSON.stringify(body) }),
  setTier: (invId: string, body: { tier: string; reason?: string }) =>
    request<{ event_id: string }>(fillRoute(ROUTES.set_investigation_tier_investigations__investigation_uid__tier_post, { investigation_uid: invId }), { method: 'POST', body: JSON.stringify(body) }),
  getTierHistory: (invId: string, limit = 100) =>
    request<{ tier_history: Array<{ from_tier: string; to_tier: string; reason?: string; occurred_at: string; actor_id: string; event_id: string }> }>(withQuery(fillRoute(ROUTES.get_tier_history_investigations__investigation_uid__tier_history_get, { investigation_uid: invId }), { limit })),
  listEvidence: async (invId: string) => {
    const evidence: Array<{
      evidence_uid: string;
      investigation_uid: string;
      created_at: string;
      original_filename: string;
      media_type: string;
      file_size_bytes: number;
    }> = [];
    let cursor: string | null = null;
    for (let i = 0; i < 50; i += 1) {
      const resp = await request<{
        evidence: Array<{
          evidence_uid: string;
          investigation_uid: string;
          created_at: string;
          original_filename: string;
          media_type: string;
          file_size_bytes: number;
        }>;
        page?: PageMeta;
      }>(withQuery(fillRoute(ROUTES.list_investigation_evidence_investigations__investigation_uid__evidence_get, { investigation_uid: invId }), { cursor }));
      evidence.push(...resp.evidence);
      cursor = resp.page?.next_cursor ?? null;
      if (!cursor) break;
    }
    return { evidence };
  },
  listClaims: async (invId: string, includeWithdrawn = true) => {
    const claims: Array<{
      claim_uid: string;
      investigation_uid: string;
      claim_text: string;
      claim_type?: string;
      current_status: string;
      created_at: string;
      updated_at: string;
      epistemic_stance?: string;
    }> = [];
    let cursor: string | null = null;
    for (let i = 0; i < 50; i += 1) {
      const resp = await request<{
        claims: Array<{
          claim_uid: string;
          investigation_uid: string;
          claim_text: string;
          claim_type?: string;
          current_status: string;
          created_at: string;
          updated_at: string;
          epistemic_stance?: string;
        }>;
        page?: PageMeta;
      }>(withQuery(fillRoute(ROUTES.list_investigation_claims_investigations__investigation_uid__claims_get, { investigation_uid: invId }), { include_withdrawn: includeWithdrawn, cursor }));
      claims.push(...resp.claims);
      cursor = resp.page?.next_cursor ?? null;
      if (!cursor) break;
    }
    return { claims };
  },
  listTensions: async (invId: string, status?: string) => {
    const tensions: Array<{
      tension_uid: string;
      claim_a_uid: string;
      claim_b_uid: string;
      tension_kind?: string;
      status: string;
      notes?: string;
      created_at: string;
      defeater_kind?: string;
    }> = [];
    let cursor: string | null = null;
    for (let i = 0; i < 50; i += 1) {
      const resp = await request<{
        tensions: Array<{
          tension_uid: string;
          claim_a_uid: string;
          claim_b_uid: string;
          tension_kind?: string;
          status: string;
          notes?: string;
          created_at: string;
          defeater_kind?: string;
        }>;
        page?: PageMeta;
      }>(withQuery(fillRoute(ROUTES.list_investigation_tensions_investigations__investigation_uid__tensions_get, { investigation_uid: invId }), { status, cursor }));
      tensions.push(...resp.tensions);
      cursor = resp.page?.next_cursor ?? null;
      if (!cursor) break;
    }
    return { tensions };
  },
  listTensionSuggestions: async (invId: string, status = 'pending') => {
    const tension_suggestions: Array<{
      suggestion_uid: string;
      claim_a_uid: string;
      claim_b_uid: string;
      suggested_tension_kind: string;
      confidence: number;
      rationale: string;
      status: string;
      created_at: string;
      confirmed_tension_uid?: string;
    }> = [];
    let cursor: string | null = null;
    for (let i = 0; i < 50; i += 1) {
      const resp = await request<{
        tension_suggestions: Array<{
          suggestion_uid: string;
          claim_a_uid: string;
          claim_b_uid: string;
          suggested_tension_kind: string;
          confidence: number;
          rationale: string;
          status: string;
          created_at: string;
          confirmed_tension_uid?: string;
        }>;
        page?: PageMeta;
      }>(withQuery(fillRoute(ROUTES.list_tension_suggestions_investigations__investigation_uid__tension_suggestions_get, { investigation_uid: invId }), { status, cursor }));
      tension_suggestions.push(...resp.tension_suggestions);
      cursor = resp.page?.next_cursor ?? null;
      if (!cursor) break;
    }
    return { tension_suggestions };
  },
  listSpans: (evidenceUid: string) =>
    request<{ spans: Array<{ span_uid: string; evidence_uid: string; anchor_type: string; created_at: string }> }>(fillRoute(ROUTES.list_evidence_spans_evidence__evidence_uid__spans_get, { evidence_uid: evidenceUid })),
  addEvidence: (invId: string, content: string, filename = 'evidence.txt') =>
    request<{ event_id: string; evidence_uid: string; span_uid: string }>(fillRoute(ROUTES.ingest_evidence_investigations__investigation_uid__evidence_post, { investigation_uid: invId }), {
      method: 'POST',
      body: JSON.stringify({ content, original_filename: filename }),
    }),
  addClaim: (invId: string, text: string, initialType?: string) =>
    request<{ event_id: string; claim_uid: string }>(fillRoute(ROUTES.propose_claim_investigations__investigation_uid__claims_post, { investigation_uid: invId }), {
      method: 'POST',
      body: JSON.stringify({ text, initial_type: initialType }),
    }),
  linkSupport: (invId: string, spanUid: string, claimUid: string, rationale?: string) =>
    request<{ event_id: string; link_uid: string }>(fillRoute(ROUTES.link_support_investigations__investigation_uid__links_support_post, { investigation_uid: invId }), {
      method: 'POST',
      body: JSON.stringify({ span_uid: spanUid, claim_uid: claimUid, rationale }),
    }),
  linkChallenge: (invId: string, spanUid: string, claimUid: string, rationale?: string) =>
    request<{ event_id: string; link_uid: string }>(fillRoute(ROUTES.link_challenge_investigations__investigation_uid__links_challenge_post, { investigation_uid: invId }), {
      method: 'POST',
      body: JSON.stringify({ span_uid: spanUid, claim_uid: claimUid, rationale }),
    }),
  declareTension: (invId: string, claimA: string, claimB: string, tensionKind = 'contradiction') =>
    request<{ event_id: string; tension_uid: string }>(fillRoute(ROUTES.declare_tension_investigations__investigation_uid__tensions_post, { investigation_uid: invId }), {
      method: 'POST',
      body: JSON.stringify({ claim_a_uid: claimA, claim_b_uid: claimB, tension_kind: tensionKind }),
    }),
  dismissTensionSuggestion: (invId: string, suggestionUid: string) =>
    request<{ event_id: string }>(fillRoute(ROUTES.dismiss_tension_suggestion_investigations__investigation_uid__tension_suggestions__suggestion_uid__dismiss_post, { investigation_uid: invId, suggestion_uid: suggestionUid }), { method: 'POST' }),
  getDefensibility: (claimUid: string) =>
    request<Record<string, unknown>>(fillRoute(ROUTES.get_defensibility_claims__claim_uid__defensibility_get, { claim_uid: claimUid })),
  getClaim: (claimUid: string) =>
    request<{ claim_uid: string; claim_text: string; claim_type?: string; current_status: string; epistemic_stance?: string }>(fillRoute(ROUTES.get_claim_claims__claim_uid__get, { claim_uid: claimUid })),
  exportChronicle: (invId: string): Promise<Blob> =>
    request<Blob>(fillRoute(ROUTES.export_investigation_investigations__investigation_uid__export_post, { investigation_uid: invId }), { method: 'POST' }),
  exportSubmissionPackage: (invId: string): Promise<Blob> =>
    request<Blob>(fillRoute(ROUTES.export_submission_package_investigations__investigation_uid__submission_package_post, { investigation_uid: invId }), { method: 'POST' }),
  getEvidenceContent: async (evidenceUid: string): Promise<string> => {
    const url = `${BASE}${fillRoute(ROUTES.get_evidence_content_evidence__evidence_uid__content_get, { evidence_uid: evidenceUid })}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
    return res.text();
  },
  createSpan: (invId: string, body: { evidence_uid: string; start_char: number; end_char: number; quote?: string }) =>
    request<{ event_id: string; span_uid: string }>(fillRoute(ROUTES.create_span_investigations__investigation_uid__spans_post, { investigation_uid: invId }), { method: 'POST', body: JSON.stringify(body) }),
  getGraph: async (invId: string) => {
    let cursor: string | null = null;
    let nodes: Array<{ id: string; type: string; label: string }> = [];
    const edges: Array<{ from: string; to: string; link_type: string; link_uid: string }> = [];
    for (let i = 0; i < 50; i += 1) {
      const resp = await request<{
        nodes: Array<{ id: string; type: string; label: string }>;
        edges: Array<{ from: string; to: string; link_type: string; link_uid: string }>;
        edges_page?: PageMeta;
      }>(withQuery(fillRoute(ROUTES.get_investigation_graph_investigations__investigation_uid__graph_get, { investigation_uid: invId }), { edge_cursor: cursor }));
      if (i === 0) {
        nodes = resp.nodes;
      }
      edges.push(...resp.edges);
      cursor = resp.edges_page?.next_cursor ?? null;
      if (!cursor) break;
    }
    return { nodes, edges };
  },
};

export function downloadBlob(blob: Blob, filename: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
