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
import Landing from './pages/Landing'

import { AuthProvider } from './contexts/AuthContext';
import { ModalProvider } from './contexts/ModalContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { useYandexMetrika } from './hooks/useYandexMetrika';

export default function App(){
  // Инициализация отслеживания переходов в Яндекс Метрике
  useYandexMetrika();
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider defaultLanguage="en">
        <AuthProvider>
          <ModalProvider>
            <ThemeProvider defaultTheme="system">
              <Routes>
                <Route path="/" element={<Landing/>} />
                <Route path="/app/*" element={
                  <ProtectedRoute>
                    <MainLayout>
                      <Routes>
                        <Route path="/" element={<Dashboard/>} />
                        <Route path="/api-docs" element={<ApiDocs/>} />
                        <Route path="/token/:mint" element={<TokenDetail/>} />
                        <Route path="/settings" element={
                          <ProtectedRoute requiredRole="admin">
                            <Settings/>
                          </ProtectedRoute>
                        } />
                        <Route path="/logs" element={
                          <ProtectedRoute requiredRole="admin">
                            <Logs/>
                          </ProtectedRoute>
                        } />
                        <Route path="*" element={<div className="text-center py-12">Страница не найдена</div>} />
                      </Routes>
                    </MainLayout>
                  </ProtectedRoute>
                } />
              </Routes>
              <Toaster />
            </ThemeProvider>
          </ModalProvider>
        </AuthProvider>
      </LanguageProvider>
    </QueryClientProvider>
  )
}
