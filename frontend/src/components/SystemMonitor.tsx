import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { useLanguage } from '@/hooks/useLanguage'
import { toast } from 'sonner'

const WALLET_ADDRESS = 'DpStbQPHnZwHGw1nfxmnWai4e5unpBrUrhjsAkxL5zTq'

export default function SystemMonitor() {
  const { t } = useLanguage()
  const [copied, setCopied] = useState(false)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(WALLET_ADDRESS)
      setCopied(true)
      toast.success(t('Wallet address copied!'))
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      toast.error(t('Failed to copy'))
    }
  }

  return (
    <div className="system-monitor">
      {/* System Description */}
      <div className="system-description">
        <div className="description-header">
          <span className="description-title">{t('How It Works')}</span>
          <div className="status-dot healthy" />
        </div>

        <ul className="description-list">
          <li>{t('New Pump.Fun tokens that migrated to Pump.Fun AMM pool automatically appear in the system with Monitoring status')}</li>
          <li>{t('When minimum liquidity on external DEXs is reached, token transitions to Active status and starts receiving score')}</li>
          <li>{t('Score (0-3) shows current token activity based on transactions, trading volume, data freshness and buy/sell balance')}</li>
          <li>{t('Tokens with low score (<0.3) for more than 5 hours are automatically archived')}</li>
        </ul>

        <p className="description-disclaimer">
          {t('Higher score indicates more active trading right now and arbitrage opportunities, but does not guarantee profitability. Always do your own research!')}
        </p>
      </div>

      {/* Donation Section */}
      <div className="donation-section">
        <div className="donation-header">
          <span className="donation-title">{t('Support the Project')}</span>
        </div>

        <p className="donation-text">
          {t('The service is free and under active development. If you find it useful, we would appreciate your support:')}
        </p>

        <div className="wallet-address-container">
          <code className="wallet-address">{WALLET_ADDRESS}</code>
          <button
            onClick={copyToClipboard}
            className="copy-button"
            title={t('Copy')}
          >
            {copied ? <Check className="icon" /> : <Copy className="icon" />}
          </button>
        </div>
      </div>
    </div>
  )
}