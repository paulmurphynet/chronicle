import { useEffect, useState } from 'react'

interface Step { title: string; body: string }
interface Vertical { id: string; display_name: string; description: string; steps: Step[] }
interface Guides { verticals: Vertical[] }

export function Learn() {
  const [guides, setGuides] = useState<Guides | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    fetch('/guides.json')
      .then((r) => r.json())
      .then((g) => {
        setGuides(g)
        if (g.verticals?.length && !selected) setSelected(g.verticals[0].id)
      })
      .catch(() => setGuides({ verticals: [] }))
  }, [])

  if (!guides) return <p>Loading Learn guides…</p>

  const vertical = guides.verticals.find((v) => v.id === selected)

  return (
    <div className="page-learn">
      <h2>Learn</h2>
      <p className="muted">Step-by-step guidance per vertical. Use with the Reference UI and API.</p>
      <div className="learn-layout">
        <nav className="learn-nav">
          {guides.verticals.map((v) => (
            <button
              key={v.id}
              type="button"
              className={selected === v.id ? 'active' : ''}
              onClick={() => setSelected(v.id)}
            >
              {v.display_name}
            </button>
          ))}
        </nav>
        <section className="learn-content">
          {vertical ? (
            <>
              <h3>{vertical.display_name}</h3>
              <p className="muted">{vertical.description}</p>
              <ol className="learn-steps">
                {vertical.steps.map((step, i) => (
                  <li key={i}>
                    <strong>{step.title}</strong>
                    <p>{step.body}</p>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <p className="muted">Select a vertical.</p>
          )}
        </section>
      </div>
    </div>
  )
}
