# Trading Signal Telegram Bot — Standalone Edition

Bu sürümde TradingView aboneliği ve webhook zorunlu değildir.

Uygulama:
1. Piyasa verisini kendi çeker.
2. AlphaTrend ve SuperTrend sinyallerini hesaplar.
3. SQLite'a kaydeder.
4. Telegram'a sinyal değişimi ve günlük özet gönderir.

## Veri kaynakları

- BTC/ETH: Binance public kline API
- Altın, S&P 500, Nasdaq, XU100, USDTRY: yfinance
- XU100/USD: XU100.IS / USDTRY=X oranı

## Render environment variables

Render panelinde Environment kısmına şunları ekle:

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

`WEBHOOK_SECRET` artık zorunlu değil; eski webhook testleri için kullanılabilir.

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

Telegram test:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/telegram/test" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }
```

Sinyal motorunu manuel çalıştır:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/engine/run-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }
```

Günlük özeti manuel gönder:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/summary/send-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }
```

`/summary/send-now` önce sinyal motorunu çalıştırır, sonra Telegram'a güncel özeti yollar.

## Manuel TradingView kontrolü

TradingView ücretsiz sürümde ilgili grafiği açıp aynı periyot ve default ayarlarla gözle karşılaştırabilirsin.

Başlangıç ayarları:
- BTC: BINANCE:BTCUSDT / 1D
- ETH: BINANCE:ETHUSDT / 1D
- Altın: XAUUSD veya GOLD / 1W
- SP500: SPX / 1W
- Nasdaq: NDX / 1W
- XU100/USD: BIST:XU100 / USDTRY / 1W

Veri kaynağı ve seans farkları yüzünden birebir aynı sonuç garanti değildir.
