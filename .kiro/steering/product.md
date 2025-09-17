# Product Overview

To The Moon is a Solana token scoring system that automatically tracks, analyzes, and scores tokens that have migrated from Pump.fun to DEX platforms in the Solana network.

## Core Features

- **Token Migration Monitoring**: WebSocket subscription to Pump.fun migrations, creating records with `monitoring` status
- **DEX Validation**: Validates tokens through DexScreener API, checking for WSOL/pumpfun-amm and external pools to promote to `active` status
- **Metrics Collection**: Gathers liquidity, price deltas (5m/15m), and transaction data from WSOL/SOL and USDC pairs across multiple DEXs
- **Scoring Algorithm**: Calculates token scores using weighted formulas based on liquidity, momentum, and transaction metrics
- **Automated Archival**: Archives tokens that fall below thresholds or timeout from monitoring
- **Real-time Dashboard**: React SPA with auto-refresh, sorting, pagination, and detailed token views
- **Public API**: RESTful endpoints for token data, scoring, and administrative functions

## Target Users

- Crypto traders and investors looking for emerging Solana tokens
- DeFi analysts tracking token performance and liquidity
- Automated trading systems requiring token scoring data

## Business Logic

The system focuses on tokens that have "graduated" from Pump.fun to external DEXs, as this migration typically indicates increased legitimacy and trading interest. Scoring emphasizes liquidity depth, price momentum, and transaction volume to identify promising tokens early.