import { useNavigate } from 'react-router-dom'
import { Token } from '@/types/token'
import { formatCurrency, formatPercentage, formatRelativeTime, getScoreColor } from '@/lib/utils'
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
    <div className="border rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">
                <Button variant="ghost" size="sm" onClick={() => handleSort('symbol')} className="h-8 px-2">
                  Token
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              <TableHead className="w-[100px] text-right">
                <Button variant="ghost" size="sm" onClick={() => handleSort('score')} className="h-8 px-2">
                  Score
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              <TableHead className="w-[120px] text-right">Liquidity</TableHead>
              <TableHead className="w-[100px] text-right">5m Δ</TableHead>
              <TableHead className="w-[100px] text-right">15m Δ</TableHead>
              <TableHead className="w-[80px] text-right">TX 5m</TableHead>
              <TableHead className="w-[100px]">DEX</TableHead>
              <TableHead className="w-[100px]">Status</TableHead>
              <TableHead className="w-[120px]">Age</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tokens.map((token) => (
              <TableRow
                key={token.mint_address}
                onClick={() => handleRowClick(token.mint_address)}
                className="cursor-pointer hover:bg-muted/50"
              >
                <TableCell className="font-medium">
                  <div>
                    <div className="font-semibold">{token.symbol || 'Unknown'}</div>
                    <div className="text-xs text-muted-foreground">
                      {token.mint_address.slice(0, 4)}...{token.mint_address.slice(-4)}
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <span className={`font-semibold ${getScoreColor(token.score)}`}>
                    {token.score.toFixed(2)}
                  </span>
                </TableCell>
                <TableCell className="text-right">{formatCurrency(token.liquidity_usd)}</TableCell>
                <TableCell className={`text-right font-medium ${token.delta_p_5m >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {formatPercentage(token.delta_p_5m)}
                </TableCell>
                <TableCell className={`text-right font-medium ${token.delta_p_15m >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {formatPercentage(token.delta_p_15m)}
                </TableCell>
                <TableCell className="text-right">{token.n_5m}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {token.primary_dex}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge 
                    variant={token.status === 'active' ? 'default' : token.status === 'monitoring' ? 'secondary' : 'outline'}
                    className="text-xs"
                  >
                    {token.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {formatRelativeTime(token.created_at || token.fetched_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
