#!/usr/bin/env bash
set -euo pipefail

curl -X POST "http://localhost:8000/webhook/tradingview" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "change-me-tradingview-secret",
    "symbol": "BINANCE:BTCUSDT",
    "timeframe": "1D",
    "price": 104250.55,
    "barTimeUnix": 1760000000000,
    "eventType": "SIGNAL_CHANGE",
    "alphaTrendSignal": "BUY",
    "superTrendSignal": "SELL",
    "alphaTrendChanged": true,
    "superTrendChanged": false
  }'
