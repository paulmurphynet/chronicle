export interface Investigation {
  investigation_uid: string;
  title: string;
  description?: string;
  is_archived: boolean;
  current_tier: string;
  tier_changed_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface EvidenceItem {
  evidence_uid: string;
  investigation_uid: string;
  created_at: string;
  original_filename: string;
  media_type: string;
  file_size_bytes: number;
}

export interface Claim {
  claim_uid: string;
  investigation_uid: string;
  claim_text: string;
  claim_type?: string;
  current_status: string;
  created_at: string;
  updated_at: string;
  epistemic_stance?: string;
}

export interface Tension {
  tension_uid: string;
  claim_a_uid: string;
  claim_b_uid: string;
  tension_kind?: string;
  status: string;
  notes?: string;
  created_at: string;
  defeater_kind?: string;
}

export interface TensionSuggestion {
  suggestion_uid: string;
  claim_a_uid: string;
  claim_b_uid: string;
  suggested_tension_kind: string;
  confidence: number;
  rationale: string;
  status: string;
  created_at: string;
  confirmed_tension_uid?: string;
}

export interface Span {
  span_uid: string;
  evidence_uid: string;
  anchor_type: string;
  created_at: string;
}
