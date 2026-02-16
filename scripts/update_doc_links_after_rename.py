#!/usr/bin/env python3
"""Update markdown and other text files to use new lowercase-hyphen doc filenames after rename."""
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parent.parent

# Old filename -> new filename (exact string to replace in links/paths)
RENAMES = [
    ("TO_DO.md", "to-do.md"),
    ("PROJECT_REEVALUATION.md", "project-reevaluation.md"),
    ("REEVALUATION_IMPLEMENTATION_PLAN.md", "reevaluation-implementation-plan.md"),
    ("FILENAME_CONVENTIONS.md", "filename-conventions.md"),
    ("TUTORIAL.md", "tutorial.md"),
    ("SAMPLES.md", "samples.md"),
    ("TESTING_E1_E7_OPTIONALS.md", "testing-e1-e7-optionals.md"),
    ("EPISTEMIC_VISION_AND_ROADMAP.md", "epistemic-vision-and-roadmap.md"),
    ("DOCS_AND_UX_PHASE_PLAN.md", "docs-and-ux-phase-plan.md"),
    ("DOCS_AUDIT.md", "docs-audit.md"),
    ("SPLIT_KERNEL_DECISION.md", "split-kernel-decision.md"),
    ("CONFORMANCE.md", "conformance.md"),
    ("FRONTEND_BACKEND_COVERAGE.md", "frontend-backend-coverage.md"),
    ("EPISTEMOLOGISTS_CONFERENCE_INTERVIEW.md", "thought_experiment/epistemologists-conference-interview.md"),
    ("INTEGRATING_WITH_CHRONICLE.md", "integrating-with-chronicle.md"),
    ("AIKIDO_UX_PHASES.md", "frontend-ux-phases.md"),
    ("AIKIDO_FRONTEND_EVALUATION.md", "frontend-ux-evaluation.md"),
    ("ASSESSMENT_DOCS_AND_AIKIDO.md", "assessment-docs-and-ux.md"),
    ("aikido-ux-phases.md", "frontend-ux-phases.md"),
    ("aikido-frontend-evaluation.md", "frontend-ux-evaluation.md"),
    ("REASONING_BRIEF.md", "reasoning-brief.md"),
    ("PRODUCT_IMPROVEMENT_PLAN.md", "product-improvement-plan.md"),
    ("BENCHMARK.md", "benchmark.md"),
    ("POLICY_PROFILES.md", "policy-profiles.md"),
    ("VERIFIER.md", "verifier.md"),
    ("OPTIONAL_TOOLS.md", "optional-tools.md"),
    ("FEDERATION_AND_GRAPH.md", "federation-and-graph.md"),
    ("CERTIFICATION.md", "certification.md"),
    ("SECURITY_EVALUATION.md", "security-evaluation.md"),
    ("VISION_AND_ROADMAP.md", "vision.md"),
    ("vision-and-roadmap.md", "vision.md"),
    ("GREENFIELD_DELTA.md", "greenfield-delta.md"),
    ("TOWARD_EPISTEMIC_LAYER_STRATEGY.md", "toward-epistemic-layer-strategy.md"),
    ("OSINT_FIRST.md", "osint-first.md"),
    ("SECURITY_AND_DEPLOYMENT.md", "security-and-deployment.md"),
    ("CHRONICLE_IN_AGE_OF_AI.md", "chronicle-in-age-of-ai.md"),
    ("EPISTEMIC_LAYER_GRAPH_RAG_AND_BEYOND.md", "epistemic-layer-graph-rag-and-beyond.md"),
    ("GENERIC_EXPORT.md", "generic-export.md"),
    ("GRC_EXPORT.md", "grc-export.md"),
    ("VECTOR_PROJECTION.md", "vector-projection.md"),
    ("SECURITY_REVIEW.md", "security-review.md"),
    ("QUALITY_AND_SECURITY_REVIEW.md", "quality-and-security-review.md"),
    ("POSTGRES.md", "postgres.md"),
    ("INTEGRATIONS_AND_SCALE.md", "integrations-and-scale.md"),
    ("ENCRYPTION.md", "encryption.md"),
    ("DEPLOYMENT.md", "deployment.md"),
    ("CROSS_DOMAIN_SCENARIO.md", "cross-domain-scenario.md"),
    ("COMPETITIVE_REVIEW.md", "competitive-review.md"),
    ("INNOVATION_AND_PHILOSOPHY.md", "innovation-and-philosophy.md"),
    ("GLOSSARY.md", "glossary.md"),
    ("PORTABILITY_AND_OFFLINE.md", "portability-and-offline.md"),
    ("IMPLEMENTER_GUIDE.md", "implementer-guide.md"),
    # archive
    ("EPISTEMOLOGY_IMPLEMENTATION_PLAN.md", "epistemology-implementation-plan.md"),
    ("FRONTEND_GAPS_PHASES.md", "frontend-gaps-phases.md"),
    ("KERNEL_PARING_PLAN.md", "kernel-paring-plan.md"),
    ("IMPLEMENTATION_HISTORY.md", "implementation-history.md"),
    ("ULTIMATE_POTENTIAL_PLAN.md", "ultimate-potential-plan.md"),
    ("TOWARD_EPISTEMIC_INFRASTRUCTURE.md", "toward-epistemic-infrastructure.md"),
    ("SECURITY_RED_TEAM_WORKLIST.md", "security-red-team-worklist.md"),
    ("PILOT_PLAN.md", "pilot-plan.md"),
    ("EPISTEMOLOGY_RED_TEAM.md", "epistemology-red-team.md"),
    ("EPISTEMIC_INFRASTRUCTURE_PLAN.md", "epistemic-infrastructure-plan.md"),
    ("CODE_REVIEW.md", "code-review.md"),
    ("AI_IMPLEMENTATION_PLAN.md", "ai-implementation-plan.md"),
    ("FORMAT_CHANGELOG.md", "format-changelog.md"),
    ("SECURITY_ASSESSMENT.md", "security-assessment.md"),
    ("INNOVATION_IMPLEMENTATION_PLAN.md", "innovation-implementation-plan.md"),
    ("VERTICALS_EPISTEMOLOGY_ROUNDTABLE.md", "verticals-epistemology-roundtable.md"),
    ("VERTICALS_STRATEGY.md", "verticals-strategy.md"),
    ("VERTICALS_IMPLEMENTATION_PHASES.md", "verticals-implementation-phases.md"),
    ("VERTICALS_UPGRADE_PLAN.md", "verticals-upgrade-plan.md"),
    ("VERTICALS_VALUATION.md", "verticals-valuation.md"),
    ("VERTICALS_ONBOARDING_AND_EXAMPLES.md", "verticals-onboarding-and-examples.md"),
    ("PANEL_VERTICALS_DISCUSSION.md", "panel-verticals-discussion.md"),
    ("VERTICALS_ADDITIVE_PHASES.md", "verticals-additive-phases.md"),
    # verticals
    ("WELCOME.md", "welcome.md"),
    ("START_HERE.md", "start-here.md"),
]


def main() -> None:
    # Files to process: all .md, CONTRIBUTING.md at root, README at root, pyproject if any links
    to_process: list[Path] = []
    for ext in (".md",):
        to_process.extend(REPO_ROOT.rglob(f"*{ext}"))
    to_process.extend([REPO_ROOT / "CONTRIBUTING.md", REPO_ROOT / "README.md"])
    to_process = [p for p in to_process if p.is_file() and ".git" not in p.parts]

    for path in to_process:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        original = text
        for old_name, new_name in RENAMES:
            text = text.replace(old_name, new_name)
        if text != original:
            path.write_text(text, encoding="utf-8")
            print(f"Updated: {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
