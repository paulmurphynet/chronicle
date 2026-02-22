import { api } from './api'

type Tier = 'spark' | 'forge' | 'vault'

type EvidenceDef = {
  evidence_id: string
  filename: string
  content: string
}

type LinkDef = {
  evidence_id: string
  rationale?: string
}

type ClaimDef = {
  claim_id: string
  text: string
  initial_type?: string
  supports: LinkDef[]
  challenges?: LinkDef[]
}

type TensionDef = {
  claim_a_id: string
  claim_b_id: string
  tension_kind?: string
}

export type WebAppTestCase = {
  id: string
  name: string
  blurb: string
  title: string
  description: string
  target_tier: Tier
  evidence: EvidenceDef[]
  claims: ClaimDef[]
  tensions: TensionDef[]
}

export const WEB_APP_TEST_CASES: WebAppTestCase[] = [
  {
    id: 'witness-location-conflict',
    name: 'Fictional witness location conflict',
    blurb: 'Synthetic testimony conflict with partial corroboration and open contradiction.',
    title: 'Fictional case: Halcyon Foods witness location conflict',
    description:
      'Synthetic training scenario for Halcyon Foods: multi-witness timeline conflict with CCTV and physical trace evidence to stress support/challenge+tension handling.',
    target_tier: 'forge',
    evidence: [
      {
        evidence_id: 'ev_transcript_a',
        filename: 'witness_a_transcript.txt',
        content:
          'Interview 1, 10:30. Witness A states: "At 10:05 I saw Riley Park in the kitchen by the back door, holding a red folder."',
      },
      {
        evidence_id: 'ev_transcript_b',
        filename: 'witness_b_transcript.txt',
        content:
          'Interview 2, 10:42. Witness B states: "Riley Park was outside near the tool shed from 10:04 to 10:06. I did not see Riley Park enter the building."',
      },
      {
        evidence_id: 'ev_cctv',
        filename: 'cctv_frame_log.txt',
        content:
          'CCTV camera K-2 frame log: 10:05:17 timestamp shows an individual matching Riley Park entering through the back kitchen door.',
      },
      {
        evidence_id: 'ev_soil',
        filename: 'forensics_soil_report.txt',
        content:
          'Forensics note: fresh garden soil found on Riley Park boots at 10:20. Soil profile matches shed area sample.',
      },
    ],
    claims: [
      {
        claim_id: 'cl_kitchen_1005',
        text: 'Riley Park was inside the kitchen at approximately 10:05.',
        supports: [
          { evidence_id: 'ev_transcript_a', rationale: 'Direct witness statement places Jordan in kitchen.' },
          { evidence_id: 'ev_cctv', rationale: 'Camera log indicates entry through kitchen door at 10:05:17.' },
        ],
        challenges: [
          { evidence_id: 'ev_transcript_b', rationale: 'Competing witness says Jordan remained near shed.' },
        ],
      },
      {
        claim_id: 'cl_shed_1005',
        text: 'Riley Park remained outside near the tool shed between 10:04 and 10:06.',
        supports: [
          { evidence_id: 'ev_transcript_b', rationale: 'Witness B gives explicit time-bounded location.' },
          { evidence_id: 'ev_soil', rationale: 'Soil trace is consistent with shed-area presence.' },
        ],
        challenges: [
          { evidence_id: 'ev_cctv', rationale: 'CCTV suggests Jordan entered kitchen during the same window.' },
        ],
      },
      {
        claim_id: 'cl_cctv_weight',
        text: 'The CCTV frame log materially increases confidence in a kitchen-entry event around 10:05.',
        supports: [{ evidence_id: 'ev_cctv', rationale: 'Timestamped machine-captured observation.' }],
        challenges: [{ evidence_id: 'ev_transcript_b', rationale: 'Witness testimony conflicts with camera inference.' }],
      },
    ],
    tensions: [
      {
        claim_a_id: 'cl_kitchen_1005',
        claim_b_id: 'cl_shed_1005',
        tension_kind: 'source_conflict_unadjudicated',
      },
    ],
  },
  {
    id: 'earnings-restatement-dispute',
    name: 'Fictional earnings restatement dispute',
    blurb: 'Synthetic finance disclosure conflict with auditor challenge and amended filing.',
    title: 'Fictional case: Northstar Devices earnings restatement dispute',
    description:
      'Synthetic training scenario for Northstar Devices: original filing, auditor note, amended filing, and executive statement conflict.',
    target_tier: 'forge',
    evidence: [
      {
        evidence_id: 'ev_q1_filing',
        filename: 'q1_filing_original.txt',
        content:
          'Northstar Devices original Q1 filing (Apr 15): "Revenue recognized for Q1 totaled $12.4M under contract policy 4.2."',
      },
      {
        evidence_id: 'ev_auditor_letter',
        filename: 'auditor_management_letter.txt',
        content:
          'Auditor management letter for Northstar Devices (May 02): "Recognition timing error overstates Q1 revenue by approximately $1.1M."',
      },
      {
        evidence_id: 'ev_amended_filing',
        filename: 'q1_filing_amended.txt',
        content:
          'Northstar Devices amended Q1 filing (May 10): "Restated Q1 revenue is $11.3M after correction of contract recognition timing."',
      },
      {
        evidence_id: 'ev_cfo_call',
        filename: 'earnings_call_excerpt.txt',
        content:
          'Northstar Devices earnings call excerpt (Apr 20): CFO stated, "At this time we do not anticipate any revenue restatement for Q1."',
      },
    ],
    claims: [
      {
        claim_id: 'cl_rev_124',
        text: 'Q1 revenue was correctly reported as $12.4M.',
        supports: [
          { evidence_id: 'ev_q1_filing', rationale: 'Primary filing states $12.4M.' },
          { evidence_id: 'ev_cfo_call', rationale: 'CFO statement aligns with no restatement expectation.' },
        ],
        challenges: [
          { evidence_id: 'ev_auditor_letter', rationale: 'Auditor identifies overstatement from timing error.' },
          { evidence_id: 'ev_amended_filing', rationale: 'Amended filing supersedes original figure.' },
        ],
      },
      {
        claim_id: 'cl_rev_113',
        text: 'Q1 revenue should be treated as restated to $11.3M.',
        supports: [
          { evidence_id: 'ev_auditor_letter', rationale: 'Auditor report quantifies overstatement.' },
          { evidence_id: 'ev_amended_filing', rationale: 'Official amended filing reports $11.3M.' },
        ],
        challenges: [
          { evidence_id: 'ev_q1_filing', rationale: 'Original filed number differs.' },
          { evidence_id: 'ev_cfo_call', rationale: 'Executive statement initially denied restatement expectation.' },
        ],
      },
    ],
    tensions: [
      {
        claim_a_id: 'cl_rev_124',
        claim_b_id: 'cl_rev_113',
        tension_kind: 'source_conflict_unadjudicated',
      },
    ],
  },
  {
    id: 'compliance-remediation-timeline',
    name: 'Fictional compliance remediation timeline',
    blurb: 'Synthetic control violation then remediation evidence for policy/tier workflow checks.',
    title: 'Fictional case: BlueHarbor Health compliance remediation timeline',
    description:
      'Synthetic training scenario for BlueHarbor Health: policy requirement, observed logging gap, remediation, and post-fix validation evidence.',
    target_tier: 'vault',
    evidence: [
      {
        evidence_id: 'ev_policy',
        filename: 'control_policy_3_1.txt',
        content:
          'BlueHarbor Health Control Policy 3.1: "All access to customer PII must be logged with actor ID, timestamp, and request path."',
      },
      {
        evidence_id: 'ev_gap_report',
        filename: 'siem_gap_report_2026_03_15.txt',
        content:
          'BlueHarbor SIEM daily report (Mar 15): service account svc-reporting performed 428 PII reads without actor-level audit logs.',
      },
      {
        evidence_id: 'ev_fix_ticket',
        filename: 'remediation_ticket_chg_8821.txt',
        content:
          'BlueHarbor change ticket CHG-8821 (Mar 18): logging middleware patch deployed to enforce actor-level audit fields for svc-reporting.',
      },
      {
        evidence_id: 'ev_postfix_validation',
        filename: 'post_fix_validation_2026_03_20.txt',
        content:
          'BlueHarbor post-fix validation (Mar 20): 100% of sampled PII reads include actor ID and timestamp; no missing log events detected in 48h window.',
      },
    ],
    claims: [
      {
        claim_id: 'cl_violation_detected',
        text: 'Control 3.1 was violated on Mar 15 due to missing actor-level PII access logs.',
        supports: [
          { evidence_id: 'ev_policy', rationale: 'Defines logging requirement baseline.' },
          { evidence_id: 'ev_gap_report', rationale: 'Gap report shows missing required fields.' },
        ],
      },
      {
        claim_id: 'cl_remediated',
        text: 'The logging control gap was remediated by Mar 20.',
        supports: [
          { evidence_id: 'ev_fix_ticket', rationale: 'Patch deployment recorded in approved change ticket.' },
          { evidence_id: 'ev_postfix_validation', rationale: 'Validation confirms expected telemetry fields after patch.' },
        ],
        challenges: [
          { evidence_id: 'ev_gap_report', rationale: 'Historical gap indicates prior non-compliance and may require extended monitoring.' },
        ],
      },
    ],
    tensions: [],
  },
]

export function getWebAppTestCase(caseId: string): WebAppTestCase | undefined {
  return WEB_APP_TEST_CASES.find((c) => c.id === caseId)
}

async function setInvestigationTier(investigationUid: string, targetTier: Tier): Promise<void> {
  if (targetTier === 'spark') return
  await api.setTier(investigationUid, { tier: 'forge', reason: 'Scenario seed reached structured evidence stage.' })
  if (targetTier === 'vault') {
    await api.setTier(investigationUid, { tier: 'vault', reason: 'Scenario seed prepared for publication/checkpoint review.' })
  }
}

export async function seedWebAppTestCase(caseId: string): Promise<{ investigation_uid: string; case_name: string }> {
  const scenario = getWebAppTestCase(caseId)
  if (!scenario) {
    throw new Error(`Unknown test case id: ${caseId}`)
  }

  const created = await api.createInvestigation({
    title: scenario.title,
    description: scenario.description,
    investigation_key: `web_case_${scenario.id}_${Date.now()}`,
  })
  const investigationUid = created.investigation_uid

  const spanByEvidenceId = new Map<string, string>()
  for (const ev of scenario.evidence) {
    const ingest = await api.addEvidence(investigationUid, ev.content, ev.filename)
    spanByEvidenceId.set(ev.evidence_id, ingest.span_uid)
  }

  const claimUidById = new Map<string, string>()
  for (const cl of scenario.claims) {
    const claim = await api.addClaim(investigationUid, cl.text, cl.initial_type)
    claimUidById.set(cl.claim_id, claim.claim_uid)
  }

  for (const cl of scenario.claims) {
    const claimUid = claimUidById.get(cl.claim_id)
    if (!claimUid) {
      throw new Error(`Missing claim uid for seeded claim id: ${cl.claim_id}`)
    }

    for (const support of cl.supports) {
      const spanUid = spanByEvidenceId.get(support.evidence_id)
      if (!spanUid) {
        throw new Error(`Missing evidence span for support link: ${support.evidence_id}`)
      }
      await api.linkSupport(investigationUid, spanUid, claimUid, support.rationale)
    }

    for (const challenge of cl.challenges ?? []) {
      const spanUid = spanByEvidenceId.get(challenge.evidence_id)
      if (!spanUid) {
        throw new Error(`Missing evidence span for challenge link: ${challenge.evidence_id}`)
      }
      await api.linkChallenge(investigationUid, spanUid, claimUid, challenge.rationale)
    }
  }

  for (const t of scenario.tensions) {
    const claimAUid = claimUidById.get(t.claim_a_id)
    const claimBUid = claimUidById.get(t.claim_b_id)
    if (!claimAUid || !claimBUid) {
      throw new Error(`Missing claim uid for tension ${t.claim_a_id}<->${t.claim_b_id}`)
    }
    await api.declareTension(investigationUid, claimAUid, claimBUid, t.tension_kind)
  }

  await setInvestigationTier(investigationUid, scenario.target_tier)

  return { investigation_uid: investigationUid, case_name: scenario.name }
}
