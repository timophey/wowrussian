import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Container } from '@mui/material';
import HomePage from './pages/HomePage';
import ProjectPage from './pages/ProjectPage';
import ProjectsListPage from './pages/ProjectsListPage';
import PageDetailPage from './pages/PageDetailPage';

function App() {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/projects" element={<ProjectsListPage />} />
        <Route path="/project/:id" element={<ProjectPage />} />
        <Route path="/project/:projectId/page/:pageId" element={<PageDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Container>
  );
}

export default App;