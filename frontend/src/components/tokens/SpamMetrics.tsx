import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface SpamMetricsProps {
  spamPercentage?: number
  riskLevel?: 'low' | 'medium' | 'high'
  details?: {
    suspiciousTransactions?: number
    totalTransactions?: number
    flaggedAddresses?: number
    patterns?: string[]
  }
}

function getRiskColor(level: string) {
  switch (level) {
    case 'low':
      return 'text-green-600 dark:text-green-400'
    case 'medium':
      return 'text-yellow-600 dark:text-yellow-400'
    case 'high':
      return 'text-red-600 dark:text-red-400'
    default:
      return 'text-muted-foreground'
  }
}

function getRiskIcon(level: string) {
  switch (level) {
    case 'low':
      return <CheckCircle className="h-5 w-5" />
    case 'medium':
      return <AlertTriangle className="h-5 w-5" />
    case 'high':
      return <XCircle className="h-5 w-5" />
    default:
      return null
  }
}

function getRiskBadgeVariant(level: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (level) {
    case 'low':
      return 'secondary'
    case 'medium':
      return 'outline'
    case 'high':
      return 'destructive'
    default:
      return 'outline'
  }
}

export function SpamMetrics({ 
  spamPercentage = 0, 
  riskLevel = 'low',
  details 
}: SpamMetricsProps) {
  const percentage = Math.min(100, Math.max(0, spamPercentage))
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Spam Detection
          <span className={getRiskColor(riskLevel)}>
            {getRiskIcon(riskLevel)}
          </span>
        </CardTitle>
        <CardDescription>
          Analysis of suspicious activity patterns
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Spam Percentage */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Spam Score</span>
            <Badge variant={getRiskBadgeVariant(riskLevel)}>
              {riskLevel.toUpperCase()}
            </Badge>
          </div>
          
          {/* Progress Bar */}
          <div className="relative h-4 bg-muted rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${
                percentage < 30 
                  ? 'bg-green-500' 
                  : percentage < 70 
                  ? 'bg-yellow-500' 
                  : 'bg-red-500'
              }`}
              style={{ width: `${percentage}%` }}
            />
          </div>
          
          <div className="flex justify-between mt-1 text-xs text-muted-foreground">
            <span>0%</span>
            <span className="font-semibold">{percentage.toFixed(1)}%</span>
            <span>100%</span>
          </div>
        </div>

        {/* Details */}
        {details && (
          <div className="space-y-2 pt-2 border-t">
            <h4 className="text-sm font-semibold">Detection Details</h4>
            
            {details.suspiciousTransactions !== undefined && details.totalTransactions !== undefined && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Suspicious Transactions:</span>
                <span className="font-medium">
                  {details.suspiciousTransactions} / {details.totalTransactions}
                </span>
              </div>
            )}
            
            {details.flaggedAddresses !== undefined && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Flagged Addresses:</span>
                <span className="font-medium">{details.flaggedAddresses}</span>
              </div>
            )}
            
            {details.patterns && details.patterns.length > 0 && (
              <div className="mt-2">
                <span className="text-sm text-muted-foreground">Detected Patterns:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {details.patterns.map((pattern, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {pattern}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Risk Assessment */}
        <div className="pt-2 border-t">
          <div className={`text-sm ${getRiskColor(riskLevel)}`}>
            {riskLevel === 'low' && '✓ Low risk - Normal activity patterns detected'}
            {riskLevel === 'medium' && '⚠ Medium risk - Some suspicious patterns detected'}
            {riskLevel === 'high' && '✗ High risk - Multiple suspicious patterns detected'}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
