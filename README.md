# Trading Signal Telegram Bot — Standalone Edition v3

Bu sürümde TradingView aboneliği, webhook ve Binance API kullanılmaz.

Neden v3?
- Render sunucusundan Binance API'ye istek atınca bazı bölgelerde 451 hatası alınabiliyor.
- yfinance bazı sunucu ortamlarında boş veri döndürebiliyor.
- Bu sürüm doğrudan Yahoo Chart endpoint'inden veri çeker.

## Veri kaynakları

- BTC/USD: Yahoo Chart `BTC-USD`
- ETH/USD: Yahoo Chart `ETH-USD`
- Altın/USD: Yahoo Chart `GC=F`
- S&P 500: Yahoo Chart `^GSPC`
- Nasdaq 100: Yahoo Chart `^NDX`
- BIST 100/USD: `XU100.IS / TRY=X`

## Render environment variables

```env
ADMIN_TOKEN=senin-admin-token
TELEGRAM_BOT_TOKEN=telegram-bot-token
TELEGRAM_CHAT_ID=-100xxxxxxxxxx
APP_TIMEZONE=Europe/Istanbul
ENABLE_DAILY_SUMMARY=true
REPORT_HOUR=09
REPORT_MINUTE=00
DATABASE_PATH=./data/signals.sqlite3
NOTIFY_ON_FIRST_SIGNAL=false
ENABLE_SIGNAL_ENGINE=true
ENGINE_HOURS=09
MARKET_DATA_LOOKBACK_BARS=350
```

`WEBHOOK_SECRET` artık zorunlu değildir.

## Render build ayarları

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Test

Health:

```powershell
Invoke-RestMethod -Uri "https://SENIN-RENDER-URL.onrender.com/health"
```

Sinyal motoru:

```powershell
$response = Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/engine/run-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }

$response | ConvertTo-Json -Depth 20
```

Özet gönder:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/summary/send-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }
```
