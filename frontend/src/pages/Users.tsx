import { useEffect, useState } from 'react'
import { useLanguage } from '@/hooks/useLanguage'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorDisplay } from '@/components/ui/error-display'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatRelativeTime } from '@/lib/utils'
import { API_BASE_URL } from '@/lib/constants'

interface User {
  id: number
  email: string
  role: string
  auth_provider: string
  is_active: boolean
  created_at: string | null
  has_google_id: boolean
  has_password: boolean
}

interface UsersResponse {
  total: number
  users: User[]
}

export default function Users() {
  const { t } = useLanguage()
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_BASE_URL}/admin/users`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data: UsersResponse = await response.json()
      setUsers(data.users)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Failed to load users'))
    } finally {
      setIsLoading(false)
    }
  }

  if (error) {
    return (
      <ErrorDisplay
        title={t('Failed to load users')}
        message={error}
        onRetry={fetchUsers}
      />
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>{t('Users')}</span>
            <Badge variant="secondary">{t('Total users')}: {total}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 font-semibold">{t('User ID')}</th>
                    <th className="text-left p-3 font-semibold">{t('Email')}</th>
                    <th className="text-left p-3 font-semibold">{t('Role')}</th>
                    <th className="text-left p-3 font-semibold">{t('Auth Provider')}</th>
                    <th className="text-left p-3 font-semibold">{t('Status')}</th>
                    <th className="text-left p-3 font-semibold">{t('Created At')}</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-b hover:bg-muted/50">
                      <td className="p-3">{user.id}</td>
                      <td className="p-3 font-medium">{user.email}</td>
                      <td className="p-3">
                        <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
                          {t(user.role)}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <Badge variant="outline">
                          {t(user.auth_provider)}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <Badge variant={user.is_active ? 'default' : 'destructive'}>
                          {user.is_active ? t('User Active') : t('User Inactive')}
                        </Badge>
                      </td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {user.created_at ? formatRelativeTime(user.created_at) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
