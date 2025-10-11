import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import Landing from './pages/Landing'
import './index.css'

import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import { LanguageProvider } from './components/layout/LanguageProvider'
import { ThemeProvider } from './components/layout/ThemeProvider'
import { Toaster } from './components/ui/sonner'

const rootElement = document.getElementById('root')!
const path = window.location.pathname

if (path === '/' || path === '') {
  createRoot(rootElement).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <LanguageProvider defaultLanguage="en">
          <ThemeProvider defaultTheme="system">
            <Landing />
            <Toaster />
          </ThemeProvider>
        </LanguageProvider>
      </QueryClientProvider>
    </React.StrictMode>
  )
} else {
  createRoot(rootElement).render(
    <React.StrictMode>
      <BrowserRouter basename="/app">
        <App />
      </BrowserRouter>
    </React.StrictMode>
  )
}
