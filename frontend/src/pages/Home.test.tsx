import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { Home } from './Home'
import { seedWebAppTestCase } from '../lib/testCases'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../lib/api', () => ({
  api: {
    createInvestigation: vi.fn(),
    addEvidence: vi.fn(),
    addClaim: vi.fn(),
    listEvidence: vi.fn(),
    listSpans: vi.fn(),
    linkSupport: vi.fn(),
    health: vi.fn(),
  },
}))

vi.mock('../lib/testCases', () => {
  const scenario = {
    id: 'fictional_case_alpha',
    name: 'Fictional alpha scenario',
    blurb: 'Synthetic conflict case.',
    title: 'Fictional case alpha',
    description: 'Synthetic test case.',
    target_tier: 'forge',
    evidence: [{ evidence_id: 'ev1', filename: 'e1.txt', content: 'Evidence one.' }],
    claims: [{ claim_id: 'c1', text: 'Claim one.', supports: [{ evidence_id: 'ev1' }], challenges: [] }],
    tensions: [],
  }
  return {
    WEB_APP_TEST_CASES: [scenario],
    getWebAppTestCase: (id: string) => (id === scenario.id ? scenario : undefined),
    seedWebAppTestCase: vi.fn(),
  }
})

afterEach(() => {
  vi.resetAllMocks()
})

describe('Home page', () => {
  it('creates selected realistic fictional case and navigates', async () => {
    vi.mocked(seedWebAppTestCase).mockResolvedValue({
      investigation_uid: 'inv_seeded_1',
      case_name: 'Fictional alpha scenario',
    })
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )

    expect(screen.getByText(/All entities in these cases are fictional/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Create realistic case/i }))

    await waitFor(() => {
      expect(seedWebAppTestCase).toHaveBeenCalledWith('fictional_case_alpha')
    })
    expect(mockNavigate).toHaveBeenCalledWith('/investigations/inv_seeded_1', {
      state: { fromSeedCase: 'Fictional alpha scenario' },
    })
  })
})

