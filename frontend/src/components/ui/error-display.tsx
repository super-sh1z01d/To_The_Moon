import { AlertCircle, RefreshCw } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from './alert'
import { Button } from './button'
import { useLanguage } from '@/hooks/useLanguage'

interface ErrorDisplayProps {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorDisplay({ 
  title, 
  message, 
  onRetry 
}: ErrorDisplayProps) {
  const { t } = useLanguage()
  const resolvedTitle = title ?? t('Error')
  return (
    <Alert variant="destructive" className="my-4">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{resolvedTitle}</AlertTitle>
      <AlertDescription className="mt-2">
        <p>{message}</p>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="mt-3"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('Retry')}
          </Button>
        )}
      </AlertDescription>
    </Alert>
  )
}
