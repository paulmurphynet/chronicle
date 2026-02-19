import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from './api'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api pagination', () => {
  it('collects all investigation pages', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          investigations: [{ investigation_uid: 'inv_1', title: 'One', is_archived: false, current_tier: 'spark' }],
          page: { limit: 1, has_more: true, next_cursor: 'next-token' },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          investigations: [{ investigation_uid: 'inv_2', title: 'Two', is_archived: false, current_tier: 'spark' }],
          page: { limit: 1, has_more: false, next_cursor: null },
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const out = await api.listInvestigations()

    expect(out.investigations.map((i) => i.investigation_uid)).toEqual(['inv_1', 'inv_2'])
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('cursor=next-token')
  })

  it('collects graph edge pages while keeping first node set', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          nodes: [{ id: 'c1', type: 'claim', label: 'Claim' }],
          edges: [{ from: 'e1', to: 'c1', link_type: 'support', link_uid: 'l1' }],
          edges_page: { limit: 1, has_more: true, next_cursor: 'edge-next' },
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          nodes: [{ id: 'IGNORED', type: 'claim', label: 'Ignored' }],
          edges: [{ from: 'e2', to: 'c1', link_type: 'challenge', link_uid: 'l2' }],
          edges_page: { limit: 1, has_more: false, next_cursor: null },
        })
      )
    vi.stubGlobal('fetch', fetchMock)

    const out = await api.getGraph('inv_1')

    expect(out.nodes).toEqual([{ id: 'c1', type: 'claim', label: 'Claim' }])
    expect(out.edges.map((e) => e.link_uid)).toEqual(['l1', 'l2'])
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('edge_cursor=edge-next')
  })
})
