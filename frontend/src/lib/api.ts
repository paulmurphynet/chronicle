const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '') || '/api';

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

export const api = {
  health: () => request<{ status: string }>('/health'),
  listInvestigations: () =>
    request<{ investigations: Array<{ investigation_uid: string; title: string; description?: string; is_archived: boolean; current_tier: string }> }>('/investigations'),
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
    }>(`/investigations/${id}`),
  createInvestigation: (body: { title: string; description?: string; investigation_key?: string }) =>
    request<{ event_id: string; investigation_uid: string }>('/investigations', { method: 'POST', body: JSON.stringify(body) }),
  setTier: (invId: string, body: { tier: string; reason?: string }) =>
    request<{ event_id: string }>(`/investigations/${invId}/tier`, { method: 'POST', body: JSON.stringify(body) }),
  getTierHistory: (invId: string, limit = 100) =>
    request<{ tier_history: Array<{ from_tier: string; to_tier: string; reason?: string; occurred_at: string; actor_id: string; event_id: string }> }>(`/investigations/${invId}/tier-history?limit=${limit}`),
  listEvidence: (invId: string) =>
    request<{ evidence: Array<{ evidence_uid: string; investigation_uid: string; created_at: string; original_filename: string; media_type: string; file_size_bytes: number }> }>(`/investigations/${invId}/evidence`),
  listClaims: (invId: string, includeWithdrawn = true) =>
    request<{ claims: Array<{ claim_uid: string; investigation_uid: string; claim_text: string; claim_type?: string; current_status: string; created_at: string; updated_at: string; epistemic_stance?: string }> }>(`/investigations/${invId}/claims?include_withdrawn=${includeWithdrawn}`),
  listTensions: (invId: string, status?: string) =>
    request<{ tensions: Array<{ tension_uid: string; claim_a_uid: string; claim_b_uid: string; tension_kind?: string; status: string; notes?: string; created_at: string; defeater_kind?: string }> }>(`/investigations/${invId}/tensions${status ? `?status=${status}` : ''}`),
  listTensionSuggestions: (invId: string, status = 'pending') =>
    request<{ tension_suggestions: Array<{ suggestion_uid: string; claim_a_uid: string; claim_b_uid: string; suggested_tension_kind: string; confidence: number; rationale: string; status: string; created_at: string; confirmed_tension_uid?: string }> }>(`/investigations/${invId}/tension-suggestions?status=${status}`),
  listSpans: (evidenceUid: string) =>
    request<{ spans: Array<{ span_uid: string; evidence_uid: string; anchor_type: string; created_at: string }> }>(`/evidence/${evidenceUid}/spans`),
  addEvidence: (invId: string, content: string, filename = 'evidence.txt') =>
    request<{ event_id: string; evidence_uid: string; span_uid: string }>(`/investigations/${invId}/evidence`, {
      method: 'POST',
      body: JSON.stringify({ content, original_filename: filename }),
    }),
  addClaim: (invId: string, text: string, initialType?: string) =>
    request<{ event_id: string; claim_uid: string }>(`/investigations/${invId}/claims`, {
      method: 'POST',
      body: JSON.stringify({ text, initial_type: initialType }),
    }),
  linkSupport: (invId: string, spanUid: string, claimUid: string, rationale?: string) =>
    request<{ event_id: string; link_uid: string }>(`/investigations/${invId}/links/support`, {
      method: 'POST',
      body: JSON.stringify({ span_uid: spanUid, claim_uid: claimUid, rationale }),
    }),
  linkChallenge: (invId: string, spanUid: string, claimUid: string, rationale?: string) =>
    request<{ event_id: string; link_uid: string }>(`/investigations/${invId}/links/challenge`, {
      method: 'POST',
      body: JSON.stringify({ span_uid: spanUid, claim_uid: claimUid, rationale }),
    }),
  declareTension: (invId: string, claimA: string, claimB: string, tensionKind = 'contradiction') =>
    request<{ event_id: string; tension_uid: string }>(`/investigations/${invId}/tensions`, {
      method: 'POST',
      body: JSON.stringify({ claim_a_uid: claimA, claim_b_uid: claimB, tension_kind: tensionKind }),
    }),
  dismissTensionSuggestion: (invId: string, suggestionUid: string) =>
    request<{ event_id: string }>(`/investigations/${invId}/tension-suggestions/${suggestionUid}/dismiss`, { method: 'POST' }),
  getDefensibility: (claimUid: string) =>
    request<Record<string, unknown>>(`/claims/${claimUid}/defensibility`),
  getClaim: (claimUid: string) =>
    request<{ claim_uid: string; claim_text: string; claim_type?: string; current_status: string; epistemic_stance?: string }>(`/claims/${claimUid}`),
  exportChronicle: (invId: string): Promise<Blob> =>
    request<Blob>(`/investigations/${invId}/export`, { method: 'POST' }),
  exportSubmissionPackage: (invId: string): Promise<Blob> =>
    request<Blob>(`/investigations/${invId}/submission-package`, { method: 'POST' }),
  getEvidenceContent: async (evidenceUid: string): Promise<string> => {
    const url = `${BASE}/evidence/${evidenceUid}/content`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
    return res.text();
  },
  createSpan: (invId: string, body: { evidence_uid: string; start_char: number; end_char: number; quote?: string }) =>
    request<{ event_id: string; span_uid: string }>(`/investigations/${invId}/spans`, { method: 'POST', body: JSON.stringify(body) }),
  getGraph: (invId: string) =>
    request<{ nodes: Array<{ id: string; type: string; label: string }>; edges: Array<{ from: string; to: string; link_type: string; link_uid: string }> }>(`/investigations/${invId}/graph`),
};

export function downloadBlob(blob: Blob, filename: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
