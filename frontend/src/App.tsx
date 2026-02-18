import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { Investigations } from './pages/Investigations'
import { InvestigationDetail } from './pages/InvestigationDetail'
import { Learn } from './pages/Learn'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="investigations" element={<Investigations />} />
        <Route path="investigations/:id" element={<InvestigationDetail />} />
        <Route path="learn" element={<Learn />} />
      </Route>
    </Routes>
  )
}

export default App
