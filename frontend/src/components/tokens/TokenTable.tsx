import { useNavigate } from 'react-router-dom'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef } from 'react'
import { Token } from '@/types/token'
import { formatCurrency, formatPercentage, formatRelativeTime, getScoreColor, getStatusColor } from '@/lib/utils'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { ArrowUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface TokenTableProps {
  tokens: Token[]
  isLoading?: boolean
  onSort?: (column: string) => void
  sortColumn?: string
  sortDirection?: 'asc' | 'desc'
}

export function TokenTable({ 
  tokens, 
  isLoading,
  onSort,
  sortColumn,
  sortDirection 
}: TokenTableProps) {
  const navigate = useNavigate()
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: tokens.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
    overscan: 5,
  })

  const handleRowClick = (mint: string) => {
    navigate(`/token/${mint}`)
  }

  const handleSort = (column: string) => {
    if (onSort) {
      onSort(column)
    }
  }

  if (isLoading) {
    return <div className="text-center py-8 text-muted-foreground">Loading...</div>
  }

  if (tokens.length === 0) {
    return <div className="text-center py-8 text-muted-foreground">No tokens found</div>
  }

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto border rounded-lg">
      <Table>
        <TableHeader className="sticky top-0 bg-background z-10">
          <TableRow>
            <TableHead>
              <Button variant="ghost" size="sm" onClick={() => handleSort('symbol')}>
                Token
                <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            </TableHead>
            <TableHead>
              <Button variant="ghost" size="sm" onClick={() => handleSort('score')}>
                Score
                <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            </TableHead>
            <TableHead>Liquidity</TableHead>
            <TableHead>5m Δ</TableHead>
            <TableHead>15m Δ</TableHead>
            <TableHead>TX 5m</TableHead>
            <TableHead>DEX</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Age</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <tr style={{ height: `${virtualizer.getTotalSize()}px` }}>
            <td />
          </tr>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const token = tokens[virtualRow.index]
            return (
              <TableRow
                key={token.mint_address}
                onClick={() => handleRowClick(token.mint_address)}
                className="cursor-pointer hover:bg-muted/50"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <TableCell className="font-medium">
                  <div>
                    <div className="font-semibold">{token.symbol || 'Unknown'}</div>
                    <div className="text-xs text-muted-foreground">
                      {token.mint_address.slice(0, 4)}...{token.mint_address.slice(-4)}
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <span className={getScoreColor(token.score)}>
                    {token.score.toFixed(2)}
                  </span>
                </TableCell>
                <TableCell>{formatCurrency(token.liquidity_usd)}</TableCell>
                <TableCell className={token.delta_p_5m >= 0 ? 'text-green-600' : 'text-red-600'}>
                  {formatPercentage(token.delta_p_5m)}
                </TableCell>
                <TableCell className={token.delta_p_15m >= 0 ? 'text-green-600' : 'text-red-600'}>
                  {formatPercentage(token.delta_p_15m)}
                </TableCell>
                <TableCell>{token.n_5m}</TableCell>
                <TableCell>
                  <Badge variant="outline">{token.primary_dex}</Badge>
                </TableCell>
                <TableCell>
                  <Badge className={getStatusColor(token.status)}>
                    {token.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {formatRelativeTime(token.created_at || token.fetched_at)}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
