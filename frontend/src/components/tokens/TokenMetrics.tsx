import { Token } from '@/types/token'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatPercentage, formatRelativeTime } from '@/lib/utils'
import { SCORE_DISPLAY_DECIMALS } from '@/lib/constants'
import { Copy, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

interface TokenMetricsProps {
  token: Token
}

export function TokenMetrics({ token }: TokenMetricsProps) {
  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    toast.success(`${label} copied to clipboard`)
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {/* Basic Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Token Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <div className="text-sm text-muted-foreground">Symbol</div>
            <div className="text-2xl font-bold">{token.symbol || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Mint Address</div>
            <div className="flex items-center gap-2">
              <code className="text-xs bg-muted px-2 py-1 rounded">
                {token.mint_address.slice(0, 8)}...{token.mint_address.slice(-8)}
              </code>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => copyToClipboard(token.mint_address, 'Address')}
              >
                <Copy className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                asChild
              >
                <a
                  href={`https://solscan.io/token/${token.mint_address}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </Button>
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Status</div>
            <Badge
              variant={token.status === 'active' ? 'default' : token.status === 'monitoring' ? 'secondary' : 'outline'}
              className="mt-1"
            >
              {token.status}
            </Badge>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Age</div>
            <div className="text-sm">{formatRelativeTime(token.created_at || token.fetched_at)}</div>
          </div>
        </CardContent>
      </Card>

      {/* Score Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Score</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <div className="text-sm text-muted-foreground">Overall Score</div>
            <div className="text-4xl font-bold text-primary">{token.score.toFixed(SCORE_DISPLAY_DECIMALS)}</div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Liquidity</span>
              <span className="font-medium">{formatCurrency(token.liquidity_usd)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Primary DEX</span>
              <Badge variant="outline" className="text-xs">{token.primary_dex}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Price Movement Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Price Movement</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <div className="text-sm text-muted-foreground">5 Minute Change</div>
            <div className={`text-2xl font-bold ${token.delta_p_5m >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {formatPercentage(token.delta_p_5m)}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">15 Minute Change</div>
            <div className={`text-2xl font-bold ${token.delta_p_15m >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {formatPercentage(token.delta_p_15m)}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Transactions (5m)</div>
            <div className="text-lg font-semibold">{token.n_5m}</div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
