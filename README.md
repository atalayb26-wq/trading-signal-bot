\
# Trading Signal Telegram Bot

Bu proje TradingView webhook alır, AlphaTrend/SuperTrend sinyallerini SQLite'a kaydeder ve Telegram kanalına:

1. Sinyal değişim uyarısı
2. Günlük sinyal özeti

gönderir.

## Mimari

```text
TradingView Alert
  ↓ Webhook
FastAPI /webhook/tradingview
  ↓
SQLite signal_states + signal_history
  ↓
Telegram Bot API
```

## Dosya yapısı

```text
app/
  main.py              FastAPI endpointleri
  storage.py           SQLite kayıt katmanı
  telegram_client.py   Telegram mesaj gönderimi
  reporting.py         Telegram mesaj formatları
  instruments.py       Parite/timeframe konfigürasyon çözümleme
  settings.py          .env ayarları

config/
  instruments.json     Parite bazlı timeframe ve sembol alias ayarları

pine/
  combined_alpha_supertrend_webhook.pine
```

## 1. Telegram bot hazırlığı

1. Telegram'da BotFather üzerinden bot oluştur.
2. Bot token'ı al.
3. Telegram kanalını oluştur.
4. Botu kanala admin olarak ekle.
5. Kanal public ise `TELEGRAM_CHAT_ID=@kanaladi` kullanabilirsin.
6. Kanal private ise numeric chat id gerekir.

## 2. Ortam ayarları

`.env.example` dosyasını `.env` olarak kopyala:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Sonra şu alanları doldur:

```env
WEBHOOK_SECRET=uzun-rastgele-bir-secret
ADMIN_TOKEN=uzun-rastgele-admin-token
TELEGRAM_BOT_TOKEN=botfather-token
TELEGRAM_CHAT_ID=@kanaladi
APP_TIMEZONE=Europe/Istanbul
REPORT_HOUR=09
REPORT_MINUTE=00
```

## 3. Lokal çalıştırma

Python 3.11+ önerilir.

### Windows PowerShell

```powershell
.\scripts\run_local.ps1
```

### macOS/Linux

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

Manuel:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows aktivasyon:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 4. Docker ile çalıştırma

```bash
docker compose up -d --build
```

Log:

```bash
docker logs -f trading-signal-bot
```

## 5. Sağlık kontrolü

```bash
curl http://localhost:8000/health
```

Beklenen çıktı:

```json
{
  "ok": true,
  "telegram_configured": true,
  "webhook_configured": true
}
```

## 6. Telegram test mesajı

Admin endpointleri `X-Admin-Token` ister.

```bash
curl -X POST "http://localhost:8000/telegram/test" \
  -H "X-Admin-Token: ADMIN_TOKEN_DEGERIN"
```

Windows PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/telegram/test" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }
```

## 7. Webhook test

`.env` içindeki `WEBHOOK_SECRET` ile test payload secret aynı olmalı.

```bash
curl -X POST "http://localhost:8000/webhook/tradingview" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "WEBHOOK_SECRET_DEGERIN",
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
```

## 8. Günlük özeti manuel gönderme

```bash
curl -X POST "http://localhost:8000/summary/send-now" \
  -H "X-Admin-Token: ADMIN_TOKEN_DEGERIN"
```

## 9. Son sinyalleri görme

```bash
curl "http://localhost:8000/signals/latest" \
  -H "X-Admin-Token: ADMIN_TOKEN_DEGERIN"
```

## 10. TradingView Pine Script kurulumu

`pine/combined_alpha_supertrend_webhook.pine` içeriğini TradingView Pine Editor'a yapıştır.

Her parite için:

1. İlgili sembolü aç.
2. İlgili timeframe'i seç.
   - Altın: 1W
   - BTC: 1D
   - ETH: 1D
   - SP500: 1W
   - Nasdaq: 1W
   - XU100/USD: 1W
3. Script'i chart'a ekle.
4. Script ayarlarında `Webhook Secret` alanını `.env` içindeki `WEBHOOK_SECRET` ile aynı yap.
5. Alert oluştur:
   - Condition: `Combined AlphaTrend + SuperTrend Webhook`
   - Seçenek: `Any alert() function call`
   - Trigger: `Once Per Bar Close`
   - Webhook URL: `https://SENIN_DOMAININ/webhook/tradingview`

Her parite/timeframe için bir alarm yeterlidir.

## 11. Public HTTPS gerekliliği

TradingView webhook'un lokal `localhost` adresine erişemez. Uygulamanın public HTTPS URL'i olmalı.

Geliştirme için seçenekler:

```text
Cloudflare Tunnel
ngrok
localtunnel
```

Canlı kullanım için:

```text
VPS + Docker + reverse proxy
```

Örnek canlı URL:

```text
https://signalbot.domain.com/webhook/tradingview
```

## 12. Parite/timeframe ayarları

`config/instruments.json` içinde her enstrümanın kendi timeframe'i vardır.

Örnek:

```json
{
  "key": "BTCUSD",
  "name": "Bitcoin/USD",
  "timeframe": "1D",
  "aliases": ["BTCUSDT", "BINANCE:BTCUSDT"]
}
```

TradingView farklı sembol gönderirse `aliases` listesine ekle.

## 13. Önemli notlar

- Bu bot yatırım tavsiyesi üretmez; sadece TradingView sinyallerini takip eder ve raporlar.
- Pine Script'teki AlphaTrend input değerlerini, TradingView'de manuel takip ettiğin orijinal indikatör ayarlarıyla eşitle.
- İlk kurulumda `sendSnapshotEveryClose=true` kalsın. Böylece son durumlar veritabanına akar.
- Snapshot mesajları Telegram'a gönderilmez; sadece DB güncellenir.
- Sinyal değişimi olursa Telegram uyarısı gelir.
- Günlük özet her gün `.env` içindeki `REPORT_HOUR:REPORT_MINUTE` saatinde gider.
