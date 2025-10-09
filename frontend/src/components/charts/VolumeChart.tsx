import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, TooltipProps } from 'recharts'
import { formatRelativeTime } from '@/lib/utils'

interface VolumeDataPoint {
  timestamp: string
  transactions: number
  volume?: number
}

interface VolumeChartProps {
  data: VolumeDataPoint[]
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
        Transactions: {data.transactions}
      </p>
      {data.volume && (
        <p className="text-sm">
          Volume: ${data.volume.toLocaleString()}
        </p>
      )}
    </div>
  )
}

export function VolumeChart({ data, title = 'Transaction Volume' }: VolumeChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No volume data available
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
          <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
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
              className="text-xs"
              stroke="currentColor"
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="transactions" 
              fill="hsl(var(--primary))" 
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
