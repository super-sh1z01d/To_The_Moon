import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, TooltipProps } from 'recharts'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'

interface LiquidityDataPoint {
  timestamp: string
  liquidity: number
}

interface LiquidityChartProps {
  data: LiquidityDataPoint[]
  title?: string
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || !payload.length) return null

  const data = payload[0].payload
  
  return (
    <div className="bg-background border rounded-lg p-3 shadow-lg">
      <p className="text-sm text-muted-foreground mb-1">
        {formatRelativeTime(data.timestamp)}
      </p>
      <p className="text-sm font-semibold">
        Liquidity: {formatCurrency(data.liquidity)}
      </p>
    </div>
  )
}

export function LiquidityChart({ data, title = 'Liquidity Trend' }: LiquidityChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No liquidity data available
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="liquidityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={(value) => {
                const date = new Date(value)
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
              }}
              className="text-xs"
              stroke="currentColor"
            />
            <YAxis 
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
              className="text-xs"
              stroke="currentColor"
            />
            <Tooltip content={<CustomTooltip />} />
            <Area 
              type="monotone" 
              dataKey="liquidity" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
              fill="url(#liquidityGradient)"
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
