import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, TooltipProps } from 'recharts'
import { formatRelativeTime } from '@/lib/utils'

interface PriceDataPoint {
  timestamp: string
  price?: number
  delta_5m?: number
  delta_15m?: number
}

interface PriceChartProps {
  data: PriceDataPoint[]
  title?: string
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || !payload.length) return null

  const data = payload[0].payload
  
  return (
    <div className="bg-background border rounded-lg p-3 shadow-lg">
      <p className="text-sm text-muted-foreground mb-2">
        {formatRelativeTime(data.timestamp)}
      </p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <div 
            className="w-3 h-3 rounded-full" 
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-sm font-medium">
            {entry.name}: {entry.value?.toFixed(2)}%
          </span>
        </div>
      ))}
    </div>
  )
}

export function PriceChart({ data, title = 'Price Movement' }: PriceChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No price data available
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
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
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
              tickFormatter={(value) => `${value.toFixed(1)}%`}
              className="text-xs"
              stroke="currentColor"
            />
            <Tooltip content={<CustomTooltip />} />
            <Line 
              type="monotone" 
              dataKey="delta_5m" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
              dot={false}
              name="5m Change"
              connectNulls
            />
            <Line 
              type="monotone" 
              dataKey="delta_15m" 
              stroke="hsl(var(--destructive))" 
              strokeWidth={2}
              dot={false}
              name="15m Change"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
