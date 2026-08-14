#!/usr/bin/env bash
set -euo pipefail

# BioCore Bot-crypto - Safe V2
# Este lanzador NO incluye modo live.
# Modos permitidos:
#   ./start_safe_v2.sh dry-run
#   ./start_safe_v2.sh backtest
#
# Requiere ejecutar desde la raíz del repositorio.

CONFIG="config/safe_dryrun_config.json"
STRATEGY="SafeTrendV2"
STRATEGY_PATH="strategies"
MODE="${1:-dry-run}"

echo "=========================================="
echo " BioCore Bot-crypto - SAFE V2"
echo "=========================================="
echo "Modo solicitado: ${MODE}"
echo "Configuración: ${CONFIG}"
echo "Estrategia: ${STRATEGY}"
echo

if [ ! -f "${CONFIG}" ]; then
    echo "ERROR: No existe ${CONFIG}"
    exit 1
fi

if [ ! -f "${STRATEGY_PATH}/${STRATEGY}.py" ]; then
    echo "ERROR: No existe ${STRATEGY_PATH}/${STRATEGY}.py"
    exit 1
fi

# Bloqueo de seguridad:
# el script se niega a arrancar si dry_run no es true.
python - <<'PY'
import json
import sys

path = "config/safe_dryrun_config.json"

with open(path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

if cfg.get("dry_run") is not True:
    print("ERROR DE SEGURIDAD: dry_run no está en true.")
    print("El lanzador SAFE V2 se niega a continuar.")
    sys.exit(1)

if cfg.get("trading_mode") != "spot":
    print("ERROR DE SEGURIDAD: trading_mode debe ser 'spot'.")
    sys.exit(1)

if int(cfg.get("max_open_trades", 0)) > 1:
    print("ERROR DE SEGURIDAD: max_open_trades no puede superar 1 en SAFE V2.")
    sys.exit(1)

exchange = cfg.get("exchange", {})
if exchange.get("key") or exchange.get("secret"):
    print("ERROR DE SEGURIDAD: SAFE V2 no debe contener claves reales del exchange.")
    sys.exit(1)

print("Chequeo de seguridad: OK")
PY

case "${MODE}" in
    dry-run)
        echo
        echo "Iniciando simulación. NO usa dinero real."
        exec freqtrade trade \
            --config "${CONFIG}" \
            --strategy "${STRATEGY}" \
            --strategy-path "${STRATEGY_PATH}"
        ;;

    backtest)
        echo
        echo "Ejecutando backtest. NO envía órdenes."
        exec freqtrade backtesting \
            --config "${CONFIG}" \
            --strategy "${STRATEGY}" \
            --strategy-path "${STRATEGY_PATH}"
        ;;

    *)
        echo "ERROR: modo no permitido: ${MODE}"
        echo "Usa solamente: dry-run o backtest"
        exit 2
        ;;
esac
