import { Route, Routes } from 'react-router-dom'
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

import { AuthProvider } from './contexts/AuthContext';

import { ModalProvider } from './contexts/ModalContext';

export default function App(){
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider defaultLanguage="en">
        <AuthProvider>
          <ModalProvider>
            <ThemeProvider defaultTheme="system">
              <MainLayout>
                <Routes>
                  <Route path="/" element={<Dashboard/>} />
                  <Route path="/settings" element={<Settings/>} />
                  <Route path="/logs" element={<Logs/>} />
                  <Route path="/api-docs" element={<ApiDocs/>} />
                  <Route path="/token/:mint" element={<TokenDetail/>} />
                  <Route path="*" element={<div className="text-center py-12">Страница не найдена</div>} />
                </Routes>
              </MainLayout>
              <Toaster />
            </ThemeProvider>
          </ModalProvider>
        </AuthProvider>
      </LanguageProvider>
    </QueryClientProvider>
  )
}
