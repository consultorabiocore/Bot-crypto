# Estrategia Order Flow Breakout para Freqtrade
# Análisis de flujo de órdenes + rupturas de precio

import talib
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OrderFlowBreakout(IStrategy):
    """
    Estrategia Order Flow Breakout
    Detecta flujo de órdenes y rupturas de precios
    """
    
    INTERFACE_VERSION = 3
    
    minimal_roi = {
        "0": 0.25,
        "30": 0.10,
        "60": 0.05,
        "240": 0.01
    }
    
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True
    
    timeframe = '5m'
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
    }
    
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }
    
    max_open_trades = 3
    stake_amount = 'unlimited'
    process_only_new_candles = True
    
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    bollinger_period = 20
    bollinger_stddev = 2
    volume_period = 20
    volume_threshold = 1.5
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=self.rsi_period)
        
        dataframe['bb_upperband'], dataframe['bb_middleband'], dataframe['bb_lowerband'] = talib.BBANDS(
            dataframe['close'], timeperiod=self.bollinger_period, 
            nbdevup=self.bollinger_stddev, nbdevdn=self.bollinger_stddev
        )
        
        dataframe['sma_fast'] = talib.SMA(dataframe['close'], timeperiod=7)
        dataframe['sma_slow'] = talib.SMA(dataframe['close'], timeperiod=21)
        
        dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = talib.MACD(
            dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        dataframe['volume_avg'] = dataframe['volume'].rolling(window=self.volume_period).mean()
        dataframe['atr'] = talib.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        
        dataframe['order_flow'] = dataframe.apply(
            lambda row: row['volume'] if row['close'] > row['open'] else -row['volume'],
            axis=1
        )
        
        dataframe['order_flow_cumsum'] = dataframe['order_flow'].rolling(window=20).sum()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        buy_signal = (
            (dataframe['order_flow'] > 0) and
            (dataframe['order_flow_cumsum'] > 0) and
            (dataframe['close'] > dataframe['bb_lowerband']) and
            (dataframe['close'].shift(1) <= dataframe['bb_lowerband'].shift(1)) and
            (dataframe['rsi'] > self.rsi_oversold) and
            (dataframe['rsi'] < 50) and
            (dataframe['rsi'] > dataframe['rsi'].shift(1)) and
            (dataframe['sma_fast'] > dataframe['sma_slow']) and
            (dataframe['macd'] > dataframe['macd_signal']) and
            (dataframe['volume'] > dataframe['volume_avg'] * self.volume_threshold)
        )
        
        dataframe.loc[buy_signal, 'enter_long'] = 1
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        sell_signal = (
            (dataframe['order_flow'] < 0) and
            (dataframe['order_flow_cumsum'] < 0) and
            (dataframe['close'] > dataframe['bb_upperband']) and
            (dataframe['rsi'] > self.rsi_overbought)
        )
        
        dataframe.loc[sell_signal, 'exit_long'] = 1
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                       current_rate: float, current_profit: float,
                       after_fill: bool, **kwargs) -> float:
        if current_profit > 0.02:
            return -0.015
        elif current_profit > 0.05:
            return -0.01
        return self.stoploss
