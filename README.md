# Trading Signal Telegram Bot — Standalone Edition v5

Bu sürümde tüm enstrümanlar günlük grafiğe çevrilmiştir.

## Takip periyotları

- Altın/USD: 1D
- BTC/USD: 1D
- ETH/USD: 1D
- S&P 500/USD: 1D
- Nasdaq/USD: 1D
- BIST 100/USD: 1D

## Değişen dosya

Ana değişiklik sadece şu dosyadadır:

```text
config/instruments.json
```

Her enstrüman için:

```json
"timeframe": "1D",
"engine_interval": "1d"
```

olarak güncellendi.

## Deploy

1. Bu ZIP içeriğini GitHub repo'ya yükle.
2. Eski dosyaların üzerine yaz.
3. Commit et.
4. Render → Manual Deploy → Deploy latest commit.
5. Test için:

```powershell
$response = Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/engine/run-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }

$response | ConvertTo-Json -Depth 20
```

Özet için:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://SENIN-RENDER-URL.onrender.com/summary/send-now" `
  -Headers @{ "X-Admin-Token" = "ADMIN_TOKEN_DEGERIN" }
```


## v6 görsel sinyal iyileştirmesi

Bu sürümde AL / SAT ifadelerinin yanına renkli ikon eklendi:

- `🟢 AL`
- `🔴 SAT`
- `⚪ NÖTR`
- `⚪ YOK`

Bu değişiklik hem günlük özet mesajında hem de sinyal değişim mesajlarında görünür.
