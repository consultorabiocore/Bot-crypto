# BioCore Bot-crypto — Safe V2

## Estado
Esta versión está diseñada exclusivamente para aprendizaje, backtesting y simulación.

**No usar dinero real todavía.**

## Archivos de Safe V2

- `strategies/SafeTrendV2.py` — estrategia EMA20/EMA50 + RSI + volumen.
- `config/safe_dryrun_config.json` — configuración segura en `dry_run`.
- `requirements_safe_v2.txt` — versión de Freqtrade usada por Safe V2.
- `start_safe_v2.sh` — lanzador que solo permite `dry-run` o `backtest`.

## Protecciones activas

- `dry_run: true`
- Trading spot
- Sin futuros ni apalancamiento
- Máximo 1 operación abierta
- BTC/USDT solamente
- Sin claves reales del exchange
- API desactivada
- Telegram desactivado
- El lanzador Safe V2 se niega a arrancar si se rompen varias de estas condiciones

## Flujo de validación

1. Instalar Freqtrade.
2. Descargar datos históricos de BTC/USDT.
3. Ejecutar backtest.
4. Revisar número de operaciones, beneficio/pérdida, drawdown y distribución de resultados.
5. Ajustar estrategia solo si existe una razón clara.
6. Repetir backtest en períodos diferentes.
7. Ejecutar dry-run durante un período prolongado.
8. Recién después evaluar FreqAI.
9. No habilitar dinero real hasta completar estas etapas.

## Comandos previstos

### Backtest
```bash
./start_safe_v2.sh backtest
```

### Simulación
```bash
./start_safe_v2.sh dry-run
```

## Regla principal

Un backtest positivo no demuestra que una estrategia vaya a ganar dinero en el futuro.
La meta inicial es comprobar que el sistema funciona correctamente, mide costos y evita errores graves antes de pensar en rentabilidad.
