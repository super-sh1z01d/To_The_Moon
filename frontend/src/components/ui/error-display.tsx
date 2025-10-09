import { AlertCircle, RefreshCw } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from './alert'
import { Button } from './button'

interface ErrorDisplayProps {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorDisplay({ 
  title = 'Error', 
  message, 
  onRetry 
}: ErrorDisplayProps) {
  return (
    <Alert variant="destructive" className="my-4">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
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
            Retry
          </Button>
        )}
      </AlertDescription>
    </Alert>
  )
}
