import { Link, Outlet, useLocation } from 'react-router-dom'

export function Layout() {
  const loc = useLocation()
  return (
    <div className="app">
      <header className="header">
        <h1>
          <Link to="/">Chronicle Reference UI</Link>
        </h1>
        <p className="tagline">Human-in-the-loop: claims, evidence, defensibility</p>
        <nav className="nav">
          <Link to="/" className={loc.pathname === '/' ? 'active' : ''}>Home</Link>
          <Link to="/investigations" className={loc.pathname.startsWith('/investigations') ? 'active' : ''}>Investigations</Link>
          <Link to="/learn" className={loc.pathname === '/learn' ? 'active' : ''}>Learn</Link>
          <a href={`${(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '') || '/api'}/docs`} target="_blank" rel="noreferrer">API docs</a>
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <a href="https://github.com/chronicle-app/chronicle/blob/main/docs/reference-ui-plan.md" target="_blank" rel="noreferrer">Reference UI plan</a>
        <span className="sep">·</span>
        <a href="https://github.com/chronicle-app/chronicle/blob/main/docs/api.md" target="_blank" rel="noreferrer">API</a>
      </footer>
    </div>
  )
}
