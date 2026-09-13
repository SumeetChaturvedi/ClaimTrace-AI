import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { InspectorProvider } from './components/layout/InspectorContext'
import { HomePage } from './pages/HomePage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ProjectPage } from './pages/ProjectPage'
import { InvestigationsPage } from './pages/InvestigationsPage'
import { InvestigationWorkspacePage } from './pages/InvestigationWorkspacePage'
import { SourceViewPage } from './pages/SourceViewPage'
import { DocumentSourceViewPage } from './pages/DocumentSourceViewPage'
import { InvestigationRecordPage } from './pages/InvestigationRecordPage'

function App() {
  return (
    <BrowserRouter>
      <InspectorProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectPage />} />
          <Route path="/projects/:projectId/documents/:documentId/source" element={<DocumentSourceViewPage />} />
          <Route path="/projects/:projectId/investigations" element={<InvestigationsPage />} />
          <Route
            path="/projects/:projectId/investigations/:investigationId"
            element={<InvestigationWorkspacePage />}
          />
          <Route
            path="/projects/:projectId/investigations/:investigationId/source/:chunkId"
            element={<SourceViewPage />}
          />
          <Route
            path="/projects/:projectId/investigations/:investigationId/record"
            element={<InvestigationRecordPage />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </InspectorProvider>
    </BrowserRouter>
  )
}

export default App
