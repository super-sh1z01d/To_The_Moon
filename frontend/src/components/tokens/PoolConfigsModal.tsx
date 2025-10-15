import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Copy, Loader2, Check } from 'lucide-react'
import { useLanguage } from '@/hooks/useLanguage'

interface PoolConfigsModalProps {
  open: boolean
  onClose: () => void
  mintAddress: string
  tokenSymbol?: string
}

interface PoolConfigs {
  solana_mev_bot: string
  not_arb: string
}

export function PoolConfigsModal({ open, onClose, mintAddress, tokenSymbol }: PoolConfigsModalProps) {
  const { t } = useLanguage()
  const [configs, setConfigs] = useState<PoolConfigs | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedSection, setCopiedSection] = useState<string | null>(null)

  useEffect(() => {
    if (open && mintAddress) {
      fetchConfigs()
    }
  }, [open, mintAddress])

  const fetchConfigs = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`/tokens/${mintAddress}/pool-configs`)
      if (!response.ok) {
        throw new Error('Failed to fetch pool configurations')
      }
      const data = await response.json()
      setConfigs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopy = async (content: string, section: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedSection(section)
      setTimeout(() => setCopiedSection(null), 2000)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{t('Pool Configurations')}</DialogTitle>
          <DialogDescription>
            {t('Download pool configurations for {token}', { token: tokenSymbol || mintAddress })}
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {error && (
          <div className="text-sm text-destructive py-4">
            {t('Failed to fetch pool configurations')}
          </div>
        )}

        {configs && !isLoading && (
          <Tabs defaultValue="solanamevbot" className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="solanamevbot">SolanaMevBot</TabsTrigger>
              <TabsTrigger value="notarb">NotArb</TabsTrigger>
            </TabsList>

            <TabsContent value="solanamevbot" className="flex-1 flex flex-col overflow-hidden mt-4">
              <div className="flex justify-between items-center mb-2">
                <p className="text-sm text-muted-foreground">
                  {t('TOML configuration for SolanaMevBot')}
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopy(configs.solana_mev_bot, 'solanamevbot')}
                >
                  {copiedSection === 'solanamevbot' ? (
                    <>
                      <Check className="mr-2 h-4 w-4" />
                      {t('Copied!')}
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      {t('Copy')}
                    </>
                  )}
                </Button>
              </div>
              <div className="flex-1 overflow-auto">
                <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto">
                  <code>{configs.solana_mev_bot}</code>
                </pre>
              </div>
            </TabsContent>

            <TabsContent value="notarb" className="flex-1 flex flex-col overflow-hidden mt-4">
              <div className="flex justify-between items-center mb-2">
                <p className="text-sm text-muted-foreground">
                  {t('Python list format for NotArb')}
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopy(configs.not_arb, 'notarb')}
                >
                  {copiedSection === 'notarb' ? (
                    <>
                      <Check className="mr-2 h-4 w-4" />
                      {t('Copied!')}
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      {t('Copy')}
                    </>
                  )}
                </Button>
              </div>
              <div className="flex-1 overflow-auto">
                <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto">
                  <code>{configs.not_arb}</code>
                </pre>
              </div>
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  )
}
