import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, TooltipProps, Cell } from 'recharts'

interface ScoreComponent {
  name: string
  value: number
  weight: number
  contribution: number
}

interface ScoreBreakdownProps {
  components?: ScoreComponent[]
  totalScore: number
}

const COLORS = {
  liquidity: 'hsl(var(--primary))',
  transactions: 'hsl(217, 91%, 60%)',
  momentum: 'hsl(142, 71%, 45%)',
  volume: 'hsl(262, 83%, 58%)',
  freshness: 'hsl(48, 96%, 53%)',
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || !payload.length) return null

  const data = payload[0].payload
  
  return (
    <div className="bg-background border rounded-lg p-3 shadow-lg">
      <p className="text-sm font-semibold mb-2">{data.name}</p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Value:</span>
          <span className="font-medium">{data.value.toFixed(2)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Weight:</span>
          <span className="font-medium">{(data.weight * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Contribution:</span>
          <span className="font-medium">{data.contribution.toFixed(2)}</span>
        </div>
      </div>
    </div>
  )
}

export function ScoreBreakdown({ components, totalScore }: ScoreBreakdownProps) {
  // Generate mock data if no components provided
  const data = components || [
    { name: 'Liquidity', value: 0.8, weight: 0.3, contribution: 0.24 },
    { name: 'Transactions', value: 0.6, weight: 0.25, contribution: 0.15 },
    { name: 'Momentum', value: 0.7, weight: 0.2, contribution: 0.14 },
    { name: 'Volume', value: 0.5, weight: 0.15, contribution: 0.075 },
    { name: 'Freshness', value: 0.9, weight: 0.1, contribution: 0.09 },
  ]

  const getColor = (name: string) => {
    const key = name.toLowerCase() as keyof typeof COLORS
    return COLORS[key] || 'hsl(var(--primary))'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score Breakdown</CardTitle>
        <CardDescription>
          Component contributions to total score: {totalScore.toFixed(2)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="name" 
              className="text-xs"
              stroke="currentColor"
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis 
              domain={[0, 1]}
              tickFormatter={(value) => value.toFixed(1)}
              className="text-xs"
              stroke="currentColor"
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="contribution" 
              radius={[4, 4, 0, 0]}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getColor(entry.name)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          {data.map((component) => (
            <div key={component.name} className="flex items-center gap-2">
              <div 
                className="w-3 h-3 rounded" 
                style={{ backgroundColor: getColor(component.name) }}
              />
              <span className="text-muted-foreground">{component.name}:</span>
              <span className="font-medium">{component.contribution.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
