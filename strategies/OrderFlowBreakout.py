"""Order Flow Breakout strategy for Freqtrade.

Important: the ``order_flow`` series below is a candle-level signed-volume
proxy. It is not true bid/ask footprint or level-2 order-flow data.
"""

from datetime import datetime

import talib
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy


class OrderFlowBreakout(IStrategy):
    """Long-only breakout strategy using signed volume and trend filters."""

    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "5m"
    startup_candle_count = 50
    process_only_new_candles = True
    use_custom_stoploss = True

    minimal_roi = {
        "0": 0.25,
        "30": 0.10,
        "60": 0.05,
        "240": 0.01,
    }

    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {
        "entry": "gtc",
        "exit": "gtc",
    }

    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    bollinger_period = 20
    bollinger_stddev = 2
    volume_period = 20
    volume_threshold = 1.5

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = talib.RSI(dataframe["close"], timeperiod=self.rsi_period)

        (
            dataframe["bb_upperband"],
            dataframe["bb_middleband"],
            dataframe["bb_lowerband"],
        ) = talib.BBANDS(
            dataframe["close"],
            timeperiod=self.bollinger_period,
            nbdevup=self.bollinger_stddev,
            nbdevdn=self.bollinger_stddev,
        )

        dataframe["sma_fast"] = talib.SMA(dataframe["close"], timeperiod=7)
        dataframe["sma_slow"] = talib.SMA(dataframe["close"], timeperiod=21)

        dataframe["macd"], dataframe["macd_signal"], dataframe["macd_hist"] = talib.MACD(
            dataframe["close"], fastperiod=12, slowperiod=26, signalperiod=9
        )

        dataframe["volume_avg"] = dataframe["volume"].rolling(window=self.volume_period).mean()
        dataframe["atr"] = talib.ATR(
            dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14
        )

        # Candle-level signed-volume proxy. This is intentionally named
        # ``order_flow`` for backward compatibility with existing notebooks.
        dataframe["order_flow"] = dataframe["volume"].where(
            dataframe["close"] > dataframe["open"], -dataframe["volume"]
        )
        dataframe["order_flow_cumsum"] = dataframe["order_flow"].rolling(window=20).sum()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "enter_long"] = 0

        buy_signal = (
            (dataframe["order_flow"] > 0)
            & (dataframe["order_flow_cumsum"] > 0)
            & (dataframe["close"] > dataframe["bb_lowerband"])
            & (dataframe["close"].shift(1) <= dataframe["bb_lowerband"].shift(1))
            & (dataframe["rsi"] > self.rsi_oversold)
            & (dataframe["rsi"] < 50)
            & (dataframe["rsi"] > dataframe["rsi"].shift(1))
            & (dataframe["sma_fast"] > dataframe["sma_slow"])
            & (dataframe["macd"] > dataframe["macd_signal"])
            & (dataframe["volume"] > dataframe["volume_avg"] * self.volume_threshold)
        )

        dataframe.loc[buy_signal, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0

        sell_signal = (
            (dataframe["order_flow"] < 0)
            & (dataframe["order_flow_cumsum"] < 0)
            & (dataframe["close"] > dataframe["bb_upperband"])
            & (dataframe["rsi"] > self.rsi_overbought)
        )

        dataframe.loc[sell_signal, "exit_long"] = 1
        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float:
        # Check the higher threshold first; otherwise >5% would be captured
        # by the >2% branch and could never reach the tighter stop.
        if current_profit > 0.05:
            return -0.01
        if current_profit > 0.02:
            return -0.015
        return self.stoploss
