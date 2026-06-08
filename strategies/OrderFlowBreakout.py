# Estrategia SMA Breakout - Simple pero efectiva

import talib
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class SMABreakout(IStrategy):
    """Estrategia simple basada en cruces de medias moviles"""
    
    INTERFACE_VERSION = 3
    
    minimal_roi = {
        "0": 0.20,
        "60": 0.10,
        "120": 0.05
    }
    
    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True
    
    timeframe = '15m'
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
    }
    
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }
    
    max_open_trades = 2
    stake_amount = 'unlimited'
    process_only_new_candles = True
    
    sma_short_period = 9
    sma_long_period = 21
    volume_threshold = 1.5
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['sma_short'] = talib.SMA(dataframe['close'], timeperiod=self.sma_short_period)
        dataframe['sma_long'] = talib.SMA(dataframe['close'], timeperiod=self.sma_long_period)
        dataframe['volume_avg'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=14)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        buy_signal = (
            (dataframe['sma_short'] > dataframe['sma_long']) and
            (dataframe['sma_short'].shift(1) <= dataframe['sma_long'].shift(1)) and
            (dataframe['volume'] > dataframe['volume_avg'] * self.volume_threshold) and
            (dataframe['rsi'] < 70)
        )
        
        dataframe.loc[buy_signal, 'enter_long'] = 1
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        sell_signal = (
            ((dataframe['sma_short'] < dataframe['sma_long']) and
            (dataframe['sma_short'].shift(1) >= dataframe['sma_long'].shift(1))) or
            (dataframe['rsi'] > 80)
        )
        
        dataframe.loc[sell_signal, 'exit_long'] = 1
        return dataframe
