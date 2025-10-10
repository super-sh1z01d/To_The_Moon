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
              <TableHead className="w-[100px]">Status</TableHead>
              <TableHead className="w-[120px] text-right">Liquidity</TableHead>
              <TableHead className="w-[80px] text-right">TX 5m</TableHead>
              <TableHead className="w-[120px]">DEXs</TableHead>
              <TableHead className="w-[140px]">Last Update</TableHead>
              <TableHead className="w-[80px]">Solscan</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tokens.map((token) => (
              <TableRow
                key={token.mint_address}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleRowClick(token.mint_address)}
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
                <TableCell>
                  <Badge 
                    variant="outline" 
                    className={`text-xs ${
                      token.status === 'active' 
                        ? 'border-green-500 text-green-600 dark:text-green-400' 
                        : token.status === 'monitoring'
                        ? 'border-yellow-500 text-yellow-600 dark:text-yellow-400'
                        : 'border-gray-500 text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    {token.status === 'active' ? 'Активный' : token.status === 'monitoring' ? 'Мониторинг' : 'Архивный'}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">{formatCurrency(token.liquidity_usd)}</TableCell>
                <TableCell className="text-right">{token.n_5m || 0}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {token.primary_dex || 'N/A'}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {formatRelativeTime(token.last_processed_at || token.fetched_at)}
                </TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      window.open(`https://solscan.io/token/${token.mint_address}`, '_blank')
                    }}
                  >
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
