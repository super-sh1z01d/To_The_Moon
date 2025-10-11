import { Navigate, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import { ThemeProvider } from './components/layout/ThemeProvider'
import { LanguageProvider } from './components/layout/LanguageProvider'
import { MainLayout } from './components/layout/MainLayout'
import { Toaster } from './components/ui/sonner'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import TokenDetail from './pages/TokenDetail'
import Logs from './pages/Logs'
import ApiDocs from './pages/ApiDocs'
import Landing from './pages/Landing'

export default function App(){
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider defaultLanguage="en">
        <ThemeProvider defaultTheme="system">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route element={<MainLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/api-docs" element={<ApiDocs />} />
              <Route path="/token/:mint" element={<TokenDetail />} />
              <Route path="/app" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
          <Toaster />
        </ThemeProvider>
      </LanguageProvider>
    </QueryClientProvider>
  )
}
