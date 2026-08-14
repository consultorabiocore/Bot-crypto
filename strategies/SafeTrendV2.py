from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import IStrategy


class SafeTrendV2(IStrategy):
    """
    Estrategia base conservadora para pruebas en DRY-RUN.

    Señales:
    - Tendencia: EMA20 sobre EMA50.
    - Confirmación: precio sobre EMA20.
    - Momentum: RSI entre 50 y 68 y subiendo.
    - Volumen: volumen actual sobre su media de 20 velas.

    IMPORTANTE:
    - Diseñada para spot.
    - No usa apalancamiento.
    - No garantiza beneficios.
    - Debe validarse con backtesting y dry-run antes de cualquier uso real.
    """

    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "1h"
    process_only_new_candles = True
    startup_candle_count = 60

    # Salida por ROI como red de seguridad.
    minimal_roi = {
        "0": 0.03,
        "720": 0.015,
        "1440": 0.0,
    }

    # Riesgo máximo teórico por operación.
    stoploss = -0.04

    # Seguimiento de ganancias.
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC",
    }

    plot_config = {
        "main_plot": {
            "ema20": {},
            "ema50": {},
        },
        "subplots": {
            "RSI": {
                "rsi": {},
            },
            "Volumen": {
                "volume_mean_20": {},
            },
        },
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        entry_condition = (
            (dataframe["volume"] > 0)
            & (dataframe["ema20"] > dataframe["ema50"])
            & (dataframe["close"] > dataframe["ema20"])
            & (dataframe["rsi"] >= 50)
            & (dataframe["rsi"] <= 68)
            & (dataframe["rsi"] > dataframe["rsi"].shift(1))
            & (dataframe["volume"] > dataframe["volume_mean_20"])
        )

        dataframe.loc[entry_condition, ["enter_long", "enter_tag"]] = (
            1,
            "ema20_ema50_rsi_volume",
        )

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        trend_failure = (
            (dataframe["ema20"] < dataframe["ema50"])
            | (dataframe["close"] < dataframe["ema50"])
        )

        momentum_exhaustion = dataframe["rsi"] > 75

        exit_condition = (
            (dataframe["volume"] > 0)
            & (trend_failure | momentum_exhaustion)
        )

        dataframe.loc[exit_condition, ["exit_long", "exit_tag"]] = (
            1,
            "trend_or_rsi_exit",
        )

        return dataframe
