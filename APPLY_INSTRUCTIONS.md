# Bot-crypto safe fix

This patch fixes runtime errors in both strategies and makes the default configuration safer for a small account.

## Main changes

- Replaces Pandas `and` / `or` expressions with vectorized `&` / `|` expressions.
- Enables and fixes the custom stoploss in `OrderFlowBreakout`.
- Documents that the current `order_flow` signal is a signed-volume proxy, not true bid/ask order flow.
- Removes duplicate/conflicting JSON configuration keys.
- Uses spot mode with 1 open trade, 10 USDT stake, 35 USDT dry-run wallet and a 10% reserve.
- Changes environment variable names to Freqtrade's nested environment-variable format.
- Makes live mode require an explicit local opt-in, API keys and the text confirmation `OPERAR_REAL`.
- Keeps dry-run as the default.

## Apply

From the repository root:

```bash
git checkout -b agent/fix-safe-small-capital
git apply Bot-crypto-safe-fix.patch
python -m py_compile strategies/OrderFlowBreakout.py strategies/SMA_Breakout.py
python -m json.tool config/default_config.json >/dev/null
python -m json.tool config/backtest_config.json >/dev/null
bash -n start_bot.sh
git add strategies/OrderFlowBreakout.py strategies/SMA_Breakout.py config/default_config.json config/backtest_config.json .env.example start_bot.sh
git commit -m "Fix strategies and safer small-capital config"
git push -u origin agent/fix-safe-small-capital
```

Do not enable live trading until backtests and dry-run results have been reviewed.
