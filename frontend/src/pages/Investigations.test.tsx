import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { Investigations } from './Investigations'
import { api } from '../lib/api'

vi.mock('../lib/api', () => ({
  api: {
    listInvestigations: vi.fn(),
  },
}))

afterEach(() => {
  vi.resetAllMocks()
})

describe('Investigations page', () => {
  it('renders fetched investigations', async () => {
    vi.mocked(api.listInvestigations).mockResolvedValue({
      investigations: [
        {
          investigation_uid: 'inv_1',
          title: 'Evidence Review',
          current_tier: 'spark',
          is_archived: false,
        },
      ],
    })

    render(
      <MemoryRouter>
        <Investigations />
      </MemoryRouter>
    )

    expect(screen.getByText(/Loading investigations/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(api.listInvestigations).toHaveBeenCalledTimes(1)
    })

    expect(screen.getByRole('link', { name: /Evidence Review/i })).toBeInTheDocument()
    expect(screen.getByText('spark')).toBeInTheDocument()
  })
})
