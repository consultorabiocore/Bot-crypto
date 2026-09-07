#!/usr/bin/env bash
set -euo pipefail

# Usage: ./start_bot.sh [strategy] [dry-run|backtest|live]
# Example: ./start_bot.sh OrderFlowBreakout dry-run

STRATEGY="${1:-OrderFlowBreakout}"
MODE="${2:-dry-run}"
CONFIG="config/default_config.json"
BACKTEST_CONFIG="config/backtest_config.json"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
elif [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if ! command -v freqtrade >/dev/null 2>&1; then
  echo "Error: freqtrade no está instalado o no está disponible en PATH."
  exit 1
fi

echo "🤖 Freqtrade Bot"
echo "Strategy: ${STRATEGY}"
echo "Mode: ${MODE}"

case "${MODE}" in
  backtest)
    echo "📊 Ejecutando backtesting..."
    freqtrade backtesting --strategy "${STRATEGY}" --config "${BACKTEST_CONFIG}"
    ;;

  live)
    if [[ "${ALLOW_LIVE_TRADING:-NO}" != "YES" ]]; then
      echo "Bloqueado: ALLOW_LIVE_TRADING debe ser YES en tu entorno local."
      exit 2
    fi

    if [[ -z "${FREQTRADE__EXCHANGE__KEY:-}" || -z "${FREQTRADE__EXCHANGE__SECRET:-}" ]]; then
      echo "Bloqueado: faltan las claves API de Binance."
      exit 2
    fi

    echo "⚠️  MODO LIVE: puede operar con dinero real."
    read -r -p "Escribe OPERAR_REAL para continuar: " confirmation
    if [[ "${confirmation}" != "OPERAR_REAL" ]]; then
      echo "Cancelado."
      exit 0
    fi

    export FREQTRADE__DRY_RUN=false
    freqtrade trade --strategy "${STRATEGY}" --config "${CONFIG}"
    ;;

  dry-run)
    export FREQTRADE__DRY_RUN=true
    echo "🧪 Modo simulación (dry-run)"
    freqtrade trade --strategy "${STRATEGY}" --config "${CONFIG}"
    ;;

  *)
    echo "Modo inválido: ${MODE}"
    echo "Usa: dry-run, backtest o live"
    exit 2
    ;;
esac
