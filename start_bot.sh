#!/bin/bash

# Script para iniciar el bot de trading
# Uso: ./start_bot.sh [strategy] [mode]
# Ejemplo: ./start_bot.sh OrderFlowBreakout live

STRATEGY=${1:-OrderFlowBreakout}
MODE=${2:-dry-run}

echo "🤖 Iniciando Freqtrade Bot"
echo "Strategy: $STRATEGY"
echo "Mode: $MODE"

# Activar entorno virtual
source venv/bin/activate

# Ejecutar bot
if [ "$MODE" = "live" ]; then
    echo "⚠️  MODO LIVE - DINERO REAL"
    read -p "¿Estás seguro? (escribe 'si' para confirmar): " confirmation
    if [ "$confirmation" = "si" ]; then
        freqtrade trade --strategy $STRATEGY --config config/default_config.json
    else
        echo "Cancelado."
    fi
elif [ "$MODE" = "backtest" ]; then
    echo "📊 Ejecutando backtesting..."
    freqtrade backtesting --strategy $STRATEGY --config config/backtest_config.json
else
    echo "🧪 Modo simulación (DRY RUN)"
    freqtrade trade --strategy $STRATEGY --config config/default_config.json --dry-run
fi
