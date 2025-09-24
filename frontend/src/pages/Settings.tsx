import { useEffect, useState } from 'react'
import { getDefaultSettings, getSettings, getSettingsIndividually, putSetting, recalc, SettingsMap, getActiveModel, switchModel } from '../lib/api'

const legacyKeys = [
  'weight_s','weight_l','weight_m','weight_t',
  'score_smoothing_alpha',
  'min_score',
  'min_pool_liquidity_usd',
  'hot_interval_sec','cold_interval_sec',
  'archive_below_hours','monitoring_timeout_hours',
  'activation_min_liquidity_usd',
  'notarb_min_score'
]

const hybridKeys = [
  'w_tx','w_vol','w_fresh','w_oi',
  'ewma_alpha','freshness_threshold_hours',
  'min_tx_threshold_5m','min_tx_threshold_1h',
  'min_volume_threshold_5m','min_volume_threshold_1h',
  'min_orderflow_volume_5m',
  'min_score',
  'min_pool_liquidity_usd',
  'hot_interval_sec','cold_interval_sec',
  'archive_below_hours','monitoring_timeout_hours',
  'activation_min_liquidity_usd',
  'notarb_min_score'
]

function getSettingsKeys(model: string): string[] {
  return model === 'hybrid_momentum' ? hybridKeys : legacyKeys
}

export default function Settings(){
  const [vals, setVals] = useState<SettingsMap>({})
  const [activeModel, setActiveModel] = useState<string>('legacy')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string>('')

  useEffect(()=>{ (async()=>{
    setLoading(true)
    try{ 
      const model = await getActiveModel()
      setActiveModel(model)
      
      // Load settings individually to avoid /settings/ timeout
      const keys = getSettingsKeys(model)
      const settings = await getSettingsIndividually(keys)
      setVals(settings)
    } finally{ setLoading(false) }
  })() }, [])

  const update = (k: string, v: string) => setVals(prev=>({...prev, [k]: v}))

  async function save(recalculate: boolean){
    setSaving(true); setMessage('')
    try{
      const keys = getSettingsKeys(activeModel)
      for(const k of keys){
        if(vals[k] != null){ await putSetting(k, String(vals[k])) }
      }
      if(recalculate){ await recalc() }
      setMessage(recalculate ? 'Сохранено. Пересчёт запущен.' : 'Сохранено.')
    } finally{ setSaving(false) }
  }

  async function handleModelSwitch(newModel: string){
    if(newModel === activeModel) return
    setSaving(true); setMessage('')
    try{
      await switchModel(newModel)
      setActiveModel(newModel)
      // Reload settings for new model
      const keys = getSettingsKeys(newModel)
      const settings = await getSettingsIndividually(keys)
      setVals(settings)
      setMessage(`Переключено на модель: ${newModel === 'hybrid_momentum' ? 'Hybrid Momentum' : 'Legacy'}`)
    } catch(e) {
      setMessage('Ошибка переключения модели')
    } finally{ setSaving(false) }
  }

  async function resetDefaults(){
    try{
      const defs = await getDefaultSettings()
      setVals(defs)
      setMessage('Загружены дефолтные значения (не сохранены). Нажмите Сохранить.')
    }catch(e){ setMessage('Не удалось загрузить дефолты') }
  }

  return (
    <div>
      <h2>Настройки системы скоринга</h2>
      {loading ? <p>Загрузка...</p> : (
        <div className="settings">
          <TokenLifecycleAlgorithm />
          <ModelSelector 
            activeModel={activeModel} 
            onModelChange={handleModelSwitch} 
            disabled={saving} 
          />
          <section>
            <h3>Весовые коэффициенты модели скоринга</h3>
            {activeModel === 'hybrid_momentum' ? (
              <>
                <Field label="🔥 Важность ускорения транзакций (w_tx)" type="number" hint="Насколько сильно влияет УСКОРЕНИЕ ТОРГОВОЙ АКТИВНОСТИ на итоговый скор токена. Компонент TX Acceleration сравнивает активность за последние 5 минут с часовым трендом. ПРИМЕР: если токен торговался 10 tx/мин час назад, а сейчас 30 tx/мин - это ускорение в 3 раза! ФИЛЬТРАЦИЯ: токены с активностью менее 20 tx/мин получают 0.0. Рекомендуется: 0.35 (35% от итогового скора)" k="w_tx" v={vals['w_tx']} set={update} />
                <Field label="📈 Важность роста объемов торгов (w_vol)" type="number" hint="Насколько сильно влияет РОСТ ТОРГОВОГО ОБЪЕМА на итоговый скор токена. Компонент Volume Momentum сравнивает объем за 5 минут со средним объемом за час, учитывая ликвидность пула. ПРИМЕР: если средний объем $1000/5мин, а сейчас $3000/5мин - это рост в 3 раза! ФИЛЬТРАЦИЯ: токены с объемом менее $500/5мин получают 0.0. Рекомендуется: 0.35 (35% от итогового скора)" k="w_vol" v={vals['w_vol']} set={update} />
                <Field label="🆕 Важность свежести токена (w_fresh)" type="number" hint="Насколько сильно влияет ВОЗРАСТ ТОКЕНА на итоговый скор. Компонент Token Freshness дает бонус недавно мигрировавшим с Pump.fun токенам. ПРИМЕР: токен возрастом 1 час получает бонус 0.83, возрастом 3 часа - 0.5, старше 6 часов - 0.0. БЕЗ ФИЛЬТРАЦИИ - дает шанс новым токенам. Рекомендуется: 0.15 (15% от итогового скора)" k="w_fresh" v={vals['w_fresh']} set={update} />
                <Field label="⚖️ Важность давления покупателей (w_oi)" type="number" hint="Насколько сильно влияет ДИСБАЛАНС ПОКУПОК/ПРОДАЖ на итоговый скор. Компонент Orderflow Imbalance показывает, кто доминирует - покупатели или продавцы. ПРИМЕР: $700 покупок + $300 продаж = +0.4 (давление покупателей 40%). ФИЛЬТРАЦИЯ: токены с общим объемом менее $500/5мин получают 0.0. Рекомендуется: 0.15 (15% от итогового скора)" k="w_oi" v={vals['w_oi']} set={update} />
                <WeightsSum ws={vals['w_tx']} wl={vals['w_vol']} wm={vals['w_fresh']} wt={vals['w_oi']} />
              </>
            ) : (
              <>
                <Field label="Вес волатильности (W_s)" type="number" hint="Что это: Важность ценовой волатильности в итоговом скоре. Определяет, насколько сильно краткосрочные изменения цены (за 5 минут) влияют на оценку токена." k="weight_s" v={vals['weight_s']} set={update} />
                <Field label="Вес ликвидности (W_l)" type="number" hint="Что это: Важность общей ликвидности токена в итоговом скоре. Отражает глубину рынка и возможность торговать без значительного слиппажа." k="weight_l" v={vals['weight_l']} set={update} />
                <Field label="Вес импульса (W_m)" type="number" hint="Что это: Важность ценового импульса в итоговом скоре. Сравнивает изменения цены за 5 и 15 минут для выявления ускорения или замедления движения." k="weight_m" v={vals['weight_m']} set={update} />
                <Field label="Вес частоты торгов (W_t)" type="number" hint="Что это: Важность транзакционной активности в итоговом скоре. Учитывает количество сделок за 5 минут как показатель интереса трейдеров к токену." k="weight_t" v={vals['weight_t']} set={update} />
                <WeightsSum ws={vals['weight_s']} wl={vals['weight_l']} wm={vals['weight_m']} wt={vals['weight_t']} />
              </>
            )}
            <Formula activeModel={activeModel} vals={vals} />
          </section>
          {activeModel === 'hybrid_momentum' ? (
            <section>
              <h3>🚀 Параметры сглаживания</h3>
              <Field 
                label="🎯 Скорость адаптации к изменениям (EWMA α)" 
                type="number" 
                hint="Контролирует, как быстро система реагирует на изменения VS насколько стабильны скоры. ПРИНЦИП: новый_скор = α × свежие_данные + (1-α) × предыдущий_скор. ПРИМЕРЫ: α=0.2 → очень стабильно, медленно меняется; α=0.4 → оптимальный баланс; α=0.6 → быстро реагирует на изменения. ЭФФЕКТ: снижает шум и ложные сигналы на 25-40%. Рекомендуется: 0.4" 
                k="ewma_alpha" 
                v={vals['ewma_alpha']} 
                set={update} 
              />
              <Field 
                label="🕐 Период бонуса для новых токенов (часы)" 
                type="number" 
                hint="Сколько часов после миграции с Pump.fun токен получает бонус за свежесть. ПРИМЕРЫ: при 6 часах → токен возрастом 0ч получает бонус 1.0, 3ч → 0.5, 6ч → 0.0. СТРАТЕГИИ: 4 часа = только самые свежие токены, 6 часов = стандарт, 8+ часов = мягкий режим для поиска поздних возможностей. Влияет только на компонент Token Freshness." 
                k="freshness_threshold_hours" 
                v={vals['freshness_threshold_hours']} 
                set={update} 
              />
              <HybridMomentumHelp alpha={vals['ewma_alpha']} freshness={vals['freshness_threshold_hours']} />
            </section>
          ) : (
            <section>
              <h3>📊 Параметры сглаживания</h3>
              <Field 
                label="Коэффициент сглаживания (α)" 
                type="number" 
                hint="Что это: Параметр экспоненциального скользящего среднего для сглаживания итогового скора токена. Уменьшает волатильность скоров, фильтруя кратковременные колебания. 0.1 = максимальная стабильность (медленная реакция), 0.3 = оптимальный баланс, 0.5 = быстрая адаптация к изменениям." 
                k="score_smoothing_alpha" 
                v={vals['score_smoothing_alpha']} 
                set={update} 
              />
              <SmoothingHelp alpha={vals['score_smoothing_alpha']} />
            </section>
          )}
          <section>
            <h3>🚫 Пороги жесткой фильтрации активности</h3>
            <div style={{background: '#fff3cd', border: '2px solid #ffc107', padding: 16, borderRadius: 8, marginBottom: 16}}>
              <h4 style={{margin: '0 0 12px 0', color: '#856404'}}>⚡ Настраиваемые пороги активности</h4>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16}}>
                
                <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #ffc107'}}>
                  <h5 style={{margin: '0 0 8px 0', color: '#dc3545'}}>🔥 TX Acceleration</h5>
                  <Field 
                    label="🔥 Мин. активность: транзакций за 5 мин" 
                    type="number" 
                    hint="ПОРОГ АКТИВНОСТИ для компонента TX Acceleration. Токены с меньшим количеством транзакций за 5 минут получают TX_Accel = 0.0 (исключаются). ПРИМЕРЫ: 100 = 20 tx/мин (стандарт), 150 = 30 tx/мин (строже), 50 = 10 tx/мин (мягче). ЦЕЛЬ: исключить 'мертвые' токены без реальной торговой активности." 
                    k="min_tx_threshold_5m" 
                    v={vals['min_tx_threshold_5m']} 
                    set={update} 
                  />
                  <Field 
                    label="🔥 Мин. стабильность: транзакций за час" 
                    type="number" 
                    hint="ПОРОГ СТАБИЛЬНОСТИ для компонента TX Acceleration. Токены с меньшим количеством транзакций за час получают TX_Accel = 0.0 (исключаются). ПРИМЕРЫ: 1200 = 20 tx/мин стабильно (стандарт), 1800 = 30 tx/мин (строже). ЦЕЛЬ: убедиться, что активность не случайная вспышка, а стабильный тренд." 
                    k="min_tx_threshold_1h" 
                    v={vals['min_tx_threshold_1h']} 
                    set={update} 
                  />
                </div>

                <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #ffc107'}}>
                  <h5 style={{margin: '0 0 8px 0', color: '#dc3545'}}>📈 Volume Momentum</h5>
                  <Field 
                    label="📈 Мин. объем торгов за 5 мин ($)" 
                    type="number" 
                    hint="ПОРОГ ОБЪЕМА для компонента Volume Momentum. Токены с меньшим торговым объемом за 5 минут получают Vol_Momentum = 0.0 (исключаются). ПРИМЕРЫ: $500 = стандарт, $750 = строже (только крупные объемы), $250 = мягче. ЦЕЛЬ: исключить токены с мизерными объемами, где нет реального интереса трейдеров." 
                    k="min_volume_threshold_5m" 
                    v={vals['min_volume_threshold_5m']} 
                    set={update} 
                  />
                  <Field 
                    label="📈 Мин. стабильный объем за час ($)" 
                    type="number" 
                    hint="ПОРОГ СТАБИЛЬНОСТИ для компонента Volume Momentum. Токены с меньшим торговым объемом за час получают Vol_Momentum = 0.0 (исключаются). ПРИМЕРЫ: $2000 = стандарт (пропорционально 20 tx/мин), $3000 = строже. ЦЕЛЬ: убедиться, что объемы не случайная вспышка, а стабильный интерес." 
                    k="min_volume_threshold_1h" 
                    v={vals['min_volume_threshold_1h']} 
                    set={update} 
                  />
                </div>

                <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #ffc107'}}>
                  <h5 style={{margin: '0 0 8px 0', color: '#dc3545'}}>⚖️ Orderflow Imbalance</h5>
                  <Field 
                    label="Мин. объем для анализа давления ($)" 
                    type="number" 
                    hint="ПОРОГ ЗНАЧИМОСТИ для компонента Orderflow Imbalance. Токены с меньшим общим объемом (покупки + продажи) за 5 минут получают Orderflow = 0.0 (исключаются). ПРИМЕРЫ: $500 = стандарт, $750 = строже, $250 = мягче. ЦЕЛЬ: исключить шум от мелких сделок." 
                    k="min_orderflow_volume_5m" 
                    v={vals['min_orderflow_volume_5m'] || '500'} 
                    set={update} 
                  />
                  <div style={{padding: '8px 0', fontSize: '0.9em', color: '#666'}}>
                    <strong>🆕 Token Freshness:</strong> Без фильтрации<br/>
                    <em>Дает шанс новым токенам</em>
                  </div>
                </div>

              </div>
              <div style={{marginTop: 12, padding: 12, background: '#d4edda', border: '1px solid #c3e6cb', borderRadius: 4}}>
                <strong>💡 Как работает фильтрация:</strong><br/>
                <div style={{marginTop: 8, fontSize: '0.9em'}}>
                  <strong>ШАГ 1:</strong> Система получает данные о токене (транзакции, объемы)<br/>
                  <strong>ШАГ 2:</strong> Проверяет каждый компонент против порогов<br/>
                  <strong>ШАГ 3:</strong> Если порог не достигнут → компонент = 0.0 (исключен)<br/>
                  <strong>ШАГ 4:</strong> Если порог достигнут → рассчитывается реальное значение<br/>
                  <strong>РЕЗУЛЬТАТ:</strong> Только токены с реальной активностью получают положительные скоры
                </div>
              </div>
            </div>
          </section>
          <section>
            <h3>⚙️ Параметры алгоритма</h3>
            <Field 
              label="🎯 Минимальный скор токена (многофункциональный)" 
              type="number" 
              hint="ТРОЙНАЯ ФУНКЦИЯ: 1) ДАШБОРД - токены с скором ниже скрываются из списка, 2) АРХИВАЦИЯ - токены архивируются, если долго не достигают этого скора, 3) ГОРЯЧИЕ/ХОЛОДНЫЕ - токены ≥ этого скора = горячие (обновляются чаще). ПРИМЕРЫ: 0.1 = мягкие условия, 0.2 = сбалансированный подход, 0.3 = строгие условия. ВАЖНО: это ключевой параметр системы!" 
              k="min_score" 
              v={vals['min_score']} 
              set={update} 
            />
            <Field 
              label="💧 Мин. ликвидность пула для учета ($)" 
              type="number" 
              hint="ФИЛЬТР ПУЛОВ-ПЫЛИНОК: Пулы с ликвидностью ниже этого значения игнорируются при расчете метрик токена. ПРИМЕРЫ: $500 = стандарт, $1000 = строже (только серьезные пулы), $200 = мягче. ЦЕЛЬ: исключить шум от мелких пулов, которые не влияют на реальную торговлю. Это дополнительная фильтрация поверх основных порогов активности." 
              k="min_pool_liquidity_usd" 
              v={vals['min_pool_liquidity_usd']} 
              set={update} 
            />
            <Field 
              label="🚀 Порог активации токена: ликвидность ($)" 
              type="number" 
              hint="ПЕРЕХОД ИЗ МОНИТОРИНГА В АКТИВНЫЕ: Минимальная ликвидность внешнего пула (НЕ Pump.fun) для активации токена. СТАТУСЫ: 'мониторинг' → 'активный' → начинается скоринг. ПРИМЕРЫ: $5000 = стандарт, $10000 = строже (только серьезные миграции), $2000 = мягче. ЦЕЛЬ: активировать только токены с реальным внешним интересом." 
              k="activation_min_liquidity_usd" 
              v={vals['activation_min_liquidity_usd']} 
              set={update} 
            />
          </section>
          <section>
            <h3>🤖 NotArb Bot Integration</h3>
            <Field 
              label="🤖 Порог скора для арбитражного бота" 
              type="number" 
              hint="ЭКСПОРТ В NOTARB BOT: Только токены с скором выше этого значения попадают в конфигурацию арбитражного бота (markets.json). ПРИМЕРЫ: 0.3 = много возможностей для бота, 0.5 = сбалансированный подход, 0.7 = только лучшие токены. ВАЖНО: с жесткой фильтрацией можно использовать более низкие пороги (0.3-0.5), так как неактивные токены уже исключены автоматически." 
              k="notarb_min_score" 
              v={vals['notarb_min_score']} 
              set={update} 
            />
          </section>
          <section>
            <h3>⏱️ Временные интервалы</h3>
            <Field 
              label="🔥 Как часто обновлять ГОРЯЧИЕ токены (сек)" 
              type="number" 
              hint="ГОРЯЧИЕ ТОКЕНЫ = токены со скором выше среднего, которые показывают хорошие результаты и активную торговлю. Система обновляет их чаще для быстрой реакции на изменения цены и ликвидности. ПРИМЕРЫ: 10 сек = максимальная скорость реакции, 20 сек = сбалансированный подход, 30 сек = экономия ресурсов. АВТОМАТИКА: система сама определяет горячие токены по их скору и активности." 
              k="hot_interval_sec" 
              v={vals['hot_interval_sec']} 
              set={update} 
            />
            <Field 
              label="❄️ Как часто обновлять ХОЛОДНЫЕ токены (сек)" 
              type="number" 
              hint="ХОЛОДНЫЕ ТОКЕНЫ = токены с низким скором (ниже среднего) или нулевым скором из-за фильтрации по ликвидности/объемам. Система обновляет их реже для экономии ресурсов, но продолжает отслеживать на случай восстановления активности. ПРИМЕРЫ: 60 сек = стандарт, 120 сек = больше экономии, 30 сек = чаще проверять. АВТОМАТИКА: система сама определяет холодные токены по низкому скору." 
              k="cold_interval_sec" 
              v={vals['cold_interval_sec']} 
              set={update} 
            />
            <Field 
              label="📦 Через сколько часов архивировать активные токены" 
              type="number" 
              hint="УСЛОВИЕ АРХИВАЦИИ: Если активный токен показывает скор = 0 (не проходит фильтры по ликвидности/объемам) дольше указанного времени, он архивируется (статус 'активный' → 'архив'). ПРИМЕРЫ: 24 часа = быстрая очистка неперспективных, 48 часов = дать больше шансов на восстановление, 72 часа = максимальное терпение. ЦЕЛЬ: освободить ресурсы от токенов, которые потеряли ликвидность и торговую активность." 
              k="archive_below_hours" 
              v={vals['archive_below_hours']} 
              set={update} 
            />
            <Field 
              label="⏰ Через сколько часов архивировать мониторинг" 
              type="number" 
              hint="УСЛОВИЕ АРХИВАЦИИ: Если токен в статусе 'мониторинг' не переходит в 'активный' (не появляется внешний пул на DEX) в течение указанного времени, он архивируется. ПРИМЕРЫ: 48 часов = стандартное ожидание, 72 часа = дать больше времени, 24 часа = быстрая очистка. ЛОГИКА: 'мониторинг' → ждем внешний пул → 'активный' → начинается скоринг. Если внешний пул не появился = токен не получил достаточной поддержки трейдеров." 
              k="monitoring_timeout_hours" 
              v={vals['monitoring_timeout_hours']} 
              set={update} 
            />
          </section>
          <section>
            <h3>🎮 Предустановленные режимы</h3>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16, marginBottom: 16}}>
              <PresetMode 
                title="🛡️ Консервативный"
                description="Максимальная стабильность, минимум ложных сигналов"
                settings={{
                  w_tx: '0.30', w_vol: '0.30', w_fresh: '0.20', w_oi: '0.20',
                  ewma_alpha: '0.2', freshness_threshold_hours: '4.0',
                  min_tx_threshold_5m: '150', min_tx_threshold_1h: '1800',
                  min_volume_threshold_5m: '750', min_volume_threshold_1h: '3000',
                  min_orderflow_volume_5m: '750',
                  min_score: '0.5'
                }}
                onApply={(settings) => setVals(prev => ({...prev, ...settings}))}
                disabled={saving}
              />
              <PresetMode 
                title="⚖️ Сбалансированный"
                description="Рекомендуемые настройки для большинства случаев"
                settings={{
                  w_tx: '0.35', w_vol: '0.35', w_fresh: '0.15', w_oi: '0.15',
                  ewma_alpha: '0.4', freshness_threshold_hours: '6.0',
                  min_tx_threshold_5m: '100', min_tx_threshold_1h: '1200',
                  min_volume_threshold_5m: '500', min_volume_threshold_1h: '2000',
                  min_orderflow_volume_5m: '500',
                  min_score: '0.3'
                }}
                onApply={(settings) => setVals(prev => ({...prev, ...settings}))}
                disabled={saving}
              />
              <PresetMode 
                title="🚀 Агрессивный"
                description="Максимальная чувствительность, больше возможностей"
                settings={{
                  w_tx: '0.40', w_vol: '0.40', w_fresh: '0.10', w_oi: '0.10',
                  ewma_alpha: '0.5', freshness_threshold_hours: '8.0',
                  min_tx_threshold_5m: '50', min_tx_threshold_1h: '600',
                  min_volume_threshold_5m: '250', min_volume_threshold_1h: '1000',
                  min_orderflow_volume_5m: '250',
                  min_score: '0.2'
                }}
                onApply={(settings) => setVals(prev => ({...prev, ...settings}))}
                disabled={saving}
              />
            </div>
            <div style={{background: '#e3f2fd', padding: 12, borderRadius: 6, border: '1px solid #90caf9'}}>
              <strong>💡 Рекомендации по выбору режима:</strong><br/>
              <span style={{fontSize: '0.9em', color: '#1565c0'}}>
                • <strong>Консервативный:</strong> Если получаете слишком много ложных сигналов<br/>
                • <strong>Сбалансированный:</strong> Начните с этого режима, подходит для большинства случаев<br/>
                • <strong>Агрессивный:</strong> Если пропускаете хорошие возможности или рынок очень активный<br/>
                • Корректируйте настройки раз в неделю на основе результатов
              </span>
            </div>
          </section>
          <div className="actions">
            <button disabled={saving} onClick={()=>save(false)}>{saving? 'Сохранение...' : 'Сохранить'}</button>
            <button disabled={saving} onClick={()=>save(true)}>{saving? '...' : 'Сохранить и Пересчитать'}</button>
            <button disabled={saving} onClick={resetDefaults}>Сбросить к дефолту</button>
            {message && <span className="muted" style={{marginLeft: 8}}>{message}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

function Field({label, hint, k, v, set, type}:{label:string, hint?:string, k:string,v?:string,set:(k:string,v:string)=>void, type?: 'number'|'text'}){
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: '4px', margin: '8px 0'}}>
      <label style={{fontSize: '14px', fontWeight: '500'}}>{label}</label>
      <input 
        value={v??''} 
        onChange={e=>set(k, e.target.value)} 
        title={hint} 
        type={type||'text'} 
        step={type==='number'? '0.01' : undefined}
        style={{padding: '6px 8px', border: '1px solid #ccc', borderRadius: '4px'}}
      />
    </div>
  )
}

function Formula({activeModel, vals}:{activeModel:string, vals:SettingsMap}){
  return (
    <div style={{marginTop:8}}>
      <h4 style={{margin:'8px 0'}}>Формула скоринга</h4>
      {activeModel === 'hybrid_momentum' ? <HybridMomentumFormula vals={vals} /> : <LegacyFormula />}
    </div>
  )
}

function HybridMomentumFormula({vals}:{vals:SettingsMap}){
  const wTx = vals['w_tx'] || '0.25'
  const wVol = vals['w_vol'] || '0.25'
  const wFresh = vals['w_fresh'] || '0.25'
  const wOi = vals['w_oi'] || '0.25'
  const alpha = vals['ewma_alpha'] || '0.3'
  const freshness = vals['freshness_threshold_hours'] || '6.0'
  
  return (
    <div style={{background:'#f0f8ff', border:'2px solid #4a90e2', padding:16, borderRadius:8, marginTop: 12}}>
      <h4 style={{margin: '0 0 12px 0', color: '#2c5aa0'}}>🚀 Hybrid Momentum Model</h4>
      
      <div style={{background: 'white', padding: 12, borderRadius: 6, marginBottom: 12, fontFamily: 'monospace', fontSize: '0.9em'}}>
        <strong>Итоговая формула:</strong><br/>
        Score = {wTx}×TX + {wVol}×Vol + {wFresh}×Fresh + {wOi}×OI
      </div>

      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12, marginBottom: 12}}>
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '2px solid #dc3545'}}>
          <strong>🔥 TX Acceleration</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            <strong>Фильтр:</strong> tx_5m ≥ 100 AND tx_1h ≥ 1200<br/>
            <strong>Формула:</strong> log(1 + rate_5m) / log(1 + rate_1h)<br/>
            <em>Иначе = 0.0</em>
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '2px solid #dc3545'}}>
          <strong>📈 Volume Momentum</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            <strong>Фильтр:</strong> vol_5m ≥ $500 AND vol_1h ≥ $2000<br/>
            <strong>Формула:</strong> (vol_5m / avg_vol) × √liquidity_factor<br/>
            <em>Иначе = 0.0</em>
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #28a745'}}>
          <strong>🆕 Token Freshness</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            <strong>Без фильтра</strong> - работает всегда<br/>
            <strong>Формула:</strong> max(0, 1 - hours/{freshness})<br/>
            <em>Дает шанс новым токенам</em>
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '2px solid #dc3545'}}>
          <strong>⚖️ Orderflow Imbalance</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            <strong>Фильтр:</strong> total_volume_5m ≥ $500<br/>
            <strong>Формула:</strong> (buys - sells) / total × significance<br/>
            <em>Иначе = 0.0</em>
          </span>
        </div>
      </div>

      <div style={{background: '#e3f2fd', padding: 10, borderRadius: 4, border: '1px solid #90caf9'}}>
        <strong>🔧 EWMA Сглаживание (α = {alpha}):</strong><br/>
        <span style={{fontSize: '0.9em'}}>
          smoothed = {alpha} × новое_значение + {(1 - parseFloat(alpha)).toFixed(1)} × предыдущее_сглаженное<br/>
          <em>Снижает шум и ложные сигналы на 25-40%</em>
        </span>
      </div>
    </div>
  )
}

function LegacyFormula(){
  return (
    <div style={{background:'#fafafa', border:'1px solid #ddd', padding:16, borderRadius:8, marginTop: 12}}>
      <h4 style={{margin: '0 0 12px 0', color: '#495057'}}>📊 Legacy Model</h4>
      
      <div style={{background: 'white', padding: 12, borderRadius: 6, marginBottom: 12, fontFamily: 'monospace', fontSize: '0.9em'}}>
        <strong>Итоговая формула:</strong><br/>
        Score = W_s×s + W_l×l + W_m×m + W_t×t
      </div>

      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 12}}>
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>📈 Волатильность (s)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Краткосрочная активность<br/>
            log(1 + |ΔP_5m| × 10) / log(11)
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>💰 Ликвидность (l)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Глубина рынка<br/>
            (log10(L_tot) − 4) / 2
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>⚡ Импульс (m)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Соотношение 5м/15м<br/>
            |ΔP_5м| / max(|ΔP_15м|, 0.01)
          </span>
        </div>
        
        <div style={{background: 'white', padding: 10, borderRadius: 4, border: '1px solid #dee2e6'}}>
          <strong>🔄 Транзакции (t)</strong><br/>
          <span style={{fontSize: '0.85em', color: '#666'}}>
            Частота торгов<br/>
            (N_5м / 5) / 300
          </span>
        </div>
      </div>

      <div style={{background: '#fff3cd', padding: 10, borderRadius: 4, border: '1px solid #ffeaa7'}}>
        <strong>📝 Особенности:</strong><br/>
        <span style={{fontSize: '0.9em'}}>
          • Все компоненты нормализованы в диапазон [0, 1]<br/>
          • Логарифмическое сглаживание волатильности<br/>
          • Защита от деления на малые числа<br/>
          • Дополнительное EWMA сглаживание итогового скора
        </span>
      </div>
    </div>
  )
}

function WeightsSum({ws, wl, wm, wt}:{ws?:string, wl?:string, wm?:string, wt?:string}){
  let sum = 0
  try{ sum = (parseFloat(ws||'0')||0) + (parseFloat(wl||'0')||0) + (parseFloat(wm||'0')||0) + (parseFloat(wt||'0')||0) }catch{}
  const ok = Math.abs(sum - 1) <= 0.05
  return <div className="muted">ΣW ≈ {sum.toFixed(2)} {ok? '' : ' (внимание: рекомендуется ≈ 1.00)'}</div>
}

function SmoothingHelp({alpha}:{alpha?:string}){
  const a = parseFloat(alpha || '0.3')
  const isValid = a >= 0 && a <= 1
  
  let description = ''
  if (!isValid) {
    description = '❌ Значение должно быть от 0.0 до 1.0'
  } else if (a <= 0.1) {
    description = '🐌 Максимальное сглаживание, очень медленная адаптация'
  } else if (a <= 0.3) {
    description = '✅ Оптимальный баланс (рекомендуется)'
  } else if (a <= 0.5) {
    description = '⚡ Быстрая адаптация, умеренное сглаживание'
  } else if (a < 1.0) {
    description = '🏃 Минимальное сглаживание'
  } else {
    description = '🚫 Без сглаживания (как было раньше)'
  }
  
  return (
    <div style={{marginTop: 8}}>
      <div className="muted" style={{fontSize: '0.9em'}}>
        {description}
      </div>
      <div style={{marginTop: 4, fontSize: '0.85em', color: '#666'}}>
        Формула: smoothed = {a.toFixed(1)} × new + {(1-a).toFixed(1)} × previous
      </div>
    </div>
  )
}



function ModelSelector({activeModel, onModelChange, disabled}:{activeModel:string, onModelChange:(model:string)=>void, disabled:boolean}){
  return (
    <section style={{marginBottom: 20, padding: 12, background: '#f0f8ff', border: '2px solid #4a90e2', borderRadius: 6}}>
      <h3 style={{margin: '0 0 12px 0', color: '#2c5aa0'}}>🎯 Модель скоринга</h3>
      <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
        <label style={{fontWeight: 'bold'}}>Активная модель:</label>
        <select 
          value={activeModel} 
          onChange={e => onModelChange(e.target.value)}
          disabled={disabled}
          style={{padding: '6px 12px', borderRadius: 4, border: '1px solid #ccc', fontSize: '14px'}}
        >
          <option value="legacy">Legacy (Классическая)</option>
          <option value="hybrid_momentum">Hybrid Momentum (Новая)</option>
        </select>
        <div style={{fontSize: '0.9em', color: '#666', marginLeft: 8}}>
          {activeModel === 'hybrid_momentum' ? 
            '🚀 4-компонентная модель с EWMA сглаживанием' : 
            '📊 Классическая модель скоринга'
          }
        </div>
      </div>
    </section>
  )
}

function TokenLifecycleAlgorithm(){
  return (
    <section style={{marginBottom: 24, padding: 16, background: '#f8f9fa', border: '2px solid #28a745', borderRadius: 8}}>
      <h3 style={{margin: '0 0 16px 0', color: '#155724', display: 'flex', alignItems: 'center', gap: 8}}>
        🔄 Алгоритм жизненного цикла токенов
      </h3>
      
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16}}>
        
        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#007bff'}}>1️⃣ Обнаружение токенов</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>WebSocket подписка на Pump.fun:</strong><br/>
            • Отслеживаем миграции токенов с Pump.fun<br/>
            • Создаем запись со статусом <code>monitoring</code><br/>
            • Начинаем отслеживание токена
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#28a745'}}>2️⃣ Активация токена</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Проверка через DexScreener:</strong><br/>
            • Ищем внешние пулы (не Pump.fun)<br/>
            • Если ликвидность ≥ порога → статус <code>active</code><br/>
            • Если нет внешних пулов → остается <code>monitoring</code>
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#ffc107'}}>3️⃣ Сбор метрик</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Агрегация данных по пулам:</strong><br/>
            • Ликвидность, объемы, транзакции<br/>
            • Фильтрация пулов-пылинок<br/>
            • Ограничение аномальных изменений
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#dc3545'}}>4️⃣ Расчет компонентов</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Hybrid Momentum модель:</strong><br/>
            • TX Acceleration - ускорение транзакций<br/>
            • Volume Momentum - импульс объема<br/>
            • Token Freshness - свежесть токена<br/>
            • Orderflow Imbalance - дисбаланс ордеров
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#6f42c1'}}>5️⃣ Сглаживание и скор</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>EWMA сглаживание:</strong><br/>
            • Стабилизация компонентов<br/>
            • Расчет итогового скора<br/>
            • Сохранение в базу данных
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#17a2b8'}}>6️⃣ Отображение</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Фильтрация для дашборда:</strong><br/>
            • Показываем токены с скором ≥ минимума<br/>
            • Сортировка по скору или компонентам<br/>
            • Визуальные индикаторы и фильтры
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#6c757d'}}>7️⃣ Архивация</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Управление жизненным циклом:</strong><br/>
            • <code>active</code> → <code>archived</code> при долгом низком скоре<br/>
            • <code>monitoring</code> → <code>archived</code> по таймауту<br/>
            • Освобождение ресурсов системы
          </div>
        </div>

        <div style={{background: 'white', padding: 12, borderRadius: 6, border: '1px solid #dee2e6'}}>
          <h4 style={{margin: '0 0 8px 0', color: '#fd7e14'}}>🔄 Обновления</h4>
          <div style={{fontSize: '0.9em', lineHeight: 1.4}}>
            <strong>Периодический пересчет:</strong><br/>
            • Активные токены - каждые 10 сек<br/>
            • Неактивные токены - каждые 60 сек<br/>
            • Адаптивная частота по скору
          </div>
        </div>

      </div>

      <div style={{marginTop: 16, padding: 12, background: '#d1ecf1', border: '1px solid #bee5eb', borderRadius: 4}}>
        <h4 style={{margin: '0 0 8px 0', color: '#0c5460'}}>💡 Ключевые принципы</h4>
        <div style={{fontSize: '0.9em', color: '#0c5460'}}>
          <strong>Автоматизация:</strong> Система работает без вмешательства пользователя<br/>
          <strong>Адаптивность:</strong> Частота обновлений зависит от активности токена<br/>
          <strong>Стабильность:</strong> EWMA сглаживание устраняет шум и ложные сигналы<br/>
          <strong>Эффективность:</strong> Архивация неактивных токенов экономит ресурсы
        </div>
      </div>
    </section>
  )
}

function HybridMomentumHelp({alpha, freshness}:{alpha?:string, freshness?:string}){
  const a = parseFloat(alpha || '0.3')
  const f = parseFloat(freshness || '6.0')
  
  return (
    <div style={{marginTop: 8, padding: 8, background: '#f0f8ff', border: '1px solid #4a90e2', borderRadius: 4}}>
      <h4 style={{margin: '0 0 8px 0', fontSize: '0.9em'}}>🚀 Hybrid Momentum параметры</h4>
      <div style={{fontSize: '0.85em', color: '#666'}}>
        <div><strong>EWMA α = {a.toFixed(2)}:</strong> {
          a <= 0.1 ? '🐌 Максимальное сглаживание' :
          a <= 0.3 ? '✅ Оптимальный баланс' :
          a <= 0.5 ? '⚡ Быстрая адаптация' : '🏃 Минимальное сглаживание'
        }</div>
        <div style={{marginTop: 4}}>
          <strong>Свежесть = {f.toFixed(1)}ч:</strong> Токены получают бонус в первые {f.toFixed(1)} часов после создания
        </div>
        <div style={{marginTop: 4}}>
          <strong>Компоненты:</strong>
          <ul style={{margin: '4px 0', paddingLeft: 16}}>
            <li>🔥 TX Acceleration - ускорение транзакций</li>
            <li>📈 Volume Momentum - моментум объёма</li>
            <li>🆕 Token Freshness - свежесть токена</li>
            <li>⚖️ Orderflow Imbalance - дисбаланс ордерфлоу</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

function PresetMode({title, description, settings, onApply, disabled}:{
  title: string,
  description: string,
  settings: SettingsMap,
  onApply: (settings: SettingsMap) => void,
  disabled: boolean
}){
  return (
    <div style={{background: 'white', padding: 16, borderRadius: 8, border: '2px solid #dee2e6'}}>
      <h4 style={{margin: '0 0 8px 0', color: '#495057'}}>{title}</h4>
      <p style={{margin: '0 0 12px 0', fontSize: '0.9em', color: '#666', lineHeight: 1.4}}>
        {description}
      </p>
      <div style={{fontSize: '0.85em', color: '#666', marginBottom: 12}}>
        <div><strong>Веса:</strong> TX={settings.w_tx}, Vol={settings.w_vol}, Fresh={settings.w_fresh}, OI={settings.w_oi}</div>
        <div><strong>EWMA α:</strong> {settings.ewma_alpha}, <strong>Свежесть:</strong> {settings.freshness_threshold_hours}ч</div>
        <div><strong>Пороги TX:</strong> {settings.min_tx_threshold_5m}/5мин, {settings.min_tx_threshold_1h}/час</div>
        <div><strong>Пороги Vol:</strong> ${settings.min_volume_threshold_5m}/5мин, ${settings.min_volume_threshold_1h}/час</div>
        <div><strong>Порог OI:</strong> ${settings.min_orderflow_volume_5m}/5мин</div>
        <div><strong>Мин. скор:</strong> {settings.min_score}</div>
      </div>
      <button 
        onClick={() => onApply(settings)}
        disabled={disabled}
        style={{
          padding: '8px 16px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: 4,
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1
        }}
      >
        Применить
      </button>
    </div>
  )
}
