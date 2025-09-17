import { ComponentBreakdown } from './api'

export function getScoreColor(score: number): string {
  if (score >= 0.5) return '#22c55e' // green
  if (score >= 0.3) return '#eab308' // yellow
  return '#ef4444' // red
}

export function getScoreClass(score: number): string {
  if (score >= 0.5) return 'score-high'
  if (score >= 0.3) return 'score-medium'
  return 'score-low'
}

export function formatAge(createdAt: string): string {
  try {
    const now = new Date()
    const created = new Date(createdAt)
    const diffMs = now.getTime() - created.getTime()
    const diffHours = diffMs / (1000 * 60 * 60)
    
    if (diffHours < 1) {
      const minutes = Math.round(diffMs / (1000 * 60))
      return `${minutes}m`
    }
    if (diffHours < 24) {
      return `${diffHours.toFixed(1)}h`
    }
    const days = diffHours / 24
    return `${days.toFixed(1)}d`
  } catch {
    return '—'
  }
}

export function isTokenFresh(createdAt: string, thresholdHours: number = 6): boolean {
  try {
    const now = new Date()
    const created = new Date(createdAt)
    const diffHours = (now.getTime() - created.getTime()) / (1000 * 60 * 60)
    return diffHours <= thresholdHours
  } catch {
    return false
  }
}

export function formatCalcTime(scoredAt?: string): string {
  if (!scoredAt) return '—'
  try {
    const date = new Date(scoredAt)
    return date.toLocaleString('sv-SE', {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace('T', ' ')
  } catch {
    return '—'
  }
}

export function formatComponent(value: number): string {
  return value.toFixed(2)
}

export function getComponentColor(value: number): string {
  // Gradient from light to dark based on component strength
  const intensity = Math.round(value * 255)
  return `rgb(${255 - intensity}, ${255 - intensity}, 255)`
}