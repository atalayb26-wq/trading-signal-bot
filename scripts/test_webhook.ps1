$body = @{
    secret = "change-me-tradingview-secret"
    symbol = "BINANCE:BTCUSDT"
    timeframe = "1D"
    price = 104250.55
    barTimeUnix = 1760000000000
    eventType = "SIGNAL_CHANGE"
    alphaTrendSignal = "BUY"
    superTrendSignal = "SELL"
    alphaTrendChanged = $true
    superTrendChanged = $false
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/webhook/tradingview" `
  -ContentType "application/json" `
  -Body $body
