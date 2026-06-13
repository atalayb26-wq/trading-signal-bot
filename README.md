# Trading Signal Telegram Bot — Standalone Edition v4

Bu sürüm TradingView aboneliği, webhook ve Binance API kullanmadan çalışır.

v4 düzeltmesi:
- BIST 100/USD için Yahoo haftalık timestamp uyuşmazlığına karşı oran önce günlük veriden hesaplanır, sonra haftalığa çevrilir.
- XU100/USD = XU100.IS / TRY=X

## Test

```powershell
$response = Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/engine/run-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }

$response | ConvertTo-Json -Depth 20
```

Beklenen:
- updated_count: 6
- error_count: 0

Özet:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/summary/send-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }
```

## Veri kaynakları

- BTC/USD: Yahoo Chart `BTC-USD`
- ETH/USD: Yahoo Chart `ETH-USD`
- Altın/USD: Yahoo Chart `GC=F`
- S&P 500: Yahoo Chart `^GSPC`
- Nasdaq 100: Yahoo Chart `^NDX`
- BIST 100/USD: `XU100.IS / TRY=X`
