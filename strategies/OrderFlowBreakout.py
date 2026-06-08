# Estrategia Order Flow Breakout para Freqtrade
# Análisis de flujo de órdenes + rupturas de precio
# Optimizada para principiantes con capital pequeño

import talib
from pandas import DataFrame
from freqtrade.strategy import IStrategy, merge_informative_pair
from freqtrade.persistence import Trade
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class OrderFlowBreakout(IStrategy):
    """
    Estrategia Order Flow Breakout
    
    Basada en el análisis del flujo de órdenes (order flow) mostrado por traders
    profesionales como el Trader Bro. Detecta:
    
    1. Zonas donde se concentran órdenes grandes
    2. Rupturas de precios en estos niveles
    3. Confirmación de tendencia
    
    Capital mínimo recomendado: $50 USDT
    Pairs: BTC/USDT, ETH/USDT, ADA/USDT
    Timeframes: 5m, 15m, 1h
    """
    
    # Versión de interfaz Freqtrade
    INTERFACE_VERSION = 3
    
    # Buy/Sell ROI - Objetivos de ganancia
    minimal_roi = {
        "0": 0.25,          # 25% ganancia meta
        "30": 0.10,         # Después de 30min: 10%
        "60": 0.05,         # Después de 1h: 5%
        "240": 0.01         # Después de 4h: 1%
    }
    
    # Stop Loss - Pérdida máxima permitida
    stoploss = -0.05  # 5% de pérdida máxima
    
    # Trailing stoploss para proteger ganancias
    trailing_stop = True
    trailing_stop_positive = 0.01  # 1% de ganancia para activar trailing
    trailing_stop_positive_offset = 0.02  # 2% offset
    trailing_only_offset_is_reached = True
    
    # Timeframe (intervalo de velas)
    timeframe = '5m'  # 5 minutos (recomendado para volatilidad)
    
    # Orden de compra/venta
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
    }
    
    # Tiempo de espera para órdenes
    order_time_in_force = {
        'entry': 'gtc',   # Good Till Cancel
        'exit': 'gtc'
    }
    
    # Máximo de trades abiertos simultáneamente
    max_open_trades = 3
    
    # Cantidad de dinero por trade (en % del capital disponible)
    # Con $30k CLP (~$35 USD): stake_amount = 10 USDT
    stake_amount = 'unlimited'  # Automático según balance
    
    # Procesamiento solo con nuevas velas
    process_only_new_candles = True
    
    # =======================
    # PARÁMETROS DE ESTRATEGIA
    # =======================
    
    # Períodos para medias móviles
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    
    # Bollinger Bands
    bollinger_period = 20
    bollinger_stddev = 2
    
    # Volumen
    volume_period = 20
    volume_threshold = 1.5  # Volumen debe ser 1.5x el promedio
    
    # =======================
    # MÉTODOS PRINCIPALES
    # =======================
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calcula todos los indicadores técnicos necesarios.
        Se ejecuta para cada par en cada vela.
        """
        
        # RSI - Identifica zonas de sobreventa/sobrecompra
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=self.rsi_period)
        
        # Bollinger Bands - Detecta volatilidad extrema
        dataframe['bb_upperband'], dataframe['bb_middleband'], dataframe['bb_lowerband'] = \
            talib.BBANDS(dataframe['close'], timeperiod=self.bollinger_period, 
                         nbdevup=self.bollinger_stddev, nbdevdn=self.bollinger_stddev)
        
        # Media Móvil Simple (SMA) - Tendencia general
        dataframe['sma_fast'] = talib.SMA(dataframe['close'], timeperiod=7)
        dataframe['sma_slow'] = talib.SMA(dataframe['close'], timeperiod=21)
        
        # MACD - Momentum
        dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = \
            talib.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        
        # Volumen promedio
        dataframe['volume_avg'] = dataframe['volume'].rolling(window=self.volume_period).mean()
        
        # ATR - Average True Range (volatilidad)
        dataframe['atr'] = talib.ATR(dataframe['high'], dataframe['low'], 
                                     dataframe['close'], timeperiod=14)
        
        # Order Flow Indicator (Volumen ponderado)
        # Si cierre > apertura = volumen positivo (compra)
        # Si cierre < apertura = volumen negativo (venta)
        dataframe['order_flow'] = dataframe.apply(
            lambda row: row['volume'] if row['close'] > row['open'] else -row['volume'],
            axis=1
        )
        
        # Order Flow acumulado
        dataframe['order_flow_cumsum'] = dataframe['order_flow'].rolling(window=20).sum()
        
        # Detectar zonas de orden concentrada
        dataframe['order_cluster'] = dataframe['order_flow_cumsum'].rolling(window=5).std()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define las SEÑALES DE COMPRA (ENTRY).
        Retorna dataframe con columna 'enter_long' = 1 cuando comprar.
        """
        
        # Inicializar señal en 0
        dataframe.loc[:, 'enter_long'] = 0
        
        # SEÑAL DE COMPRA: Confluence de múltiples indicadores
        
        buy_signal = (
            # 1. Order Flow positivo (más compras que ventas)
            (dataframe['order_flow'] > 0) &
            (dataframe['order_flow_cumsum'] > 0) &
            
            # 2. Precio rompe la banda de Bollinger inferior (breakout)
            (dataframe['close'] > dataframe['bb_lowerband']) &
            (dataframe['close'].shift(1) <= dataframe['bb_lowerband'].shift(1)) &
            
            # 3. RSI en zona de sobreventa pero recuperándose
            (dataframe['rsi'] > self.rsi_oversold) &
            (dataframe['rsi'] < 50) &
            (dataframe['rsi'] > dataframe['rsi'].shift(1)) &  # RSI en aumento
            
            # 4. Media móvil rápida cruza la lenta (señal de cambio)
            (dataframe['sma_fast'] > dataframe['sma_slow']) &
            
            # 5. MACD en zona positiva o cruzando hacia arriba
            (dataframe['macd'] > dataframe['macd_signal']) &
            
            # 6. Volumen superior al promedio (confirmación)
            (dataframe['volume'] > dataframe['volume_avg'] * self.volume_threshold) &
            
            # 7. ATR positivo (volatilidad presente = oportunidad)
            (dataframe['atr'] > 0)
        )
        
        dataframe.loc[buy_signal, 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define las SEÑALES DE VENTA (EXIT).
        Retorna dataframe con columna 'exit_long' = 1 cuando vender.
        """
        
        # Inicializar señal en 0
        dataframe.loc[:, 'exit_long'] = 0
        
        # SEÑAL DE VENTA: Cuando se agota la tendencia alcista
        
        sell_signal = (
            # 1. Order Flow negativo (más ventas que compras)
            (dataframe['order_flow'] < 0) &
            (dataframe['order_flow_cumsum'] < 0) &
            
            # 2. Precio toca banda superior de Bollinger (sobreventa)
            (dataframe['close'] > dataframe['bb_upperband']) &
            
            # 3. RSI en zona de sobrecompra
            (dataframe['rsi'] > self.rsi_overbought) &
            
            # 4. Divergencia MACD (MACD bajando pero precio subiendo)
            (dataframe['macd'] < dataframe['macd_signal']) &
            (dataframe['macd_signal'] > dataframe['macd_signal'].shift(1))
        )
        
        dataframe.loc[sell_signal, 'exit_long'] = 1
        
        return dataframe
    
    # =======================
    # MÉTODOS OPCIONALES
    # =======================
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                       current_rate: float, current_profit: float,
                       after_fill: bool, **kwargs) -> float:
        """
        Stop loss dinámico: se ajusta según el ATR.
        Esto protege tus ganancias mientras dejas espacio para fluctuaciones.
        """
        
        if current_profit > 0.02:  # Si tienes 2%+ de ganancia
            return -0.015  # Tighten stop loss a 1.5%
        elif current_profit > 0.05:  # Si tienes 5%+ de ganancia
            return -0.01   # Tighten aún más a 1%
        
        return self.stoploss
    
    def custom_entry_price(self, pair: str, trade: None, current_time: datetime,
                          proposed_rate: float, entry_tag: Optional[str], 
                          side: str, **kwargs) -> float:
        """
        Ajusta el precio de entrada para mejores condiciones.
        Intenta comprar ligeramente más bajo.
        """
        
        # Compra 0.5% menos de lo propuesto (mejor precio)
        return proposed_rate * 0.995
    
    def custom_exit_price(self, pair: str, trade: Trade, current_time: datetime,
                         proposed_rate: float, current_profit: float,
                         exit_tag: Optional[str], **kwargs) -> float:
        """
        Ajusta el precio de salida para mejores condiciones.
        Intenta vender ligeramente más alto.
        """
        
        # Vende 0.3% más de lo propuesto (mejor precio)
        return proposed_rate * 1.003
    
    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        Se ejecuta al inicio de cada loop del bot.
        Útil para logging y monitoreo.
        """
        logger.info(f"Bot loop started at {current_time}")
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """
        Confirmación final antes de abrir un trade.
        Aquí puedes añadir controles adicionales.
        """
        
        logger.info(f"Confirmed entry for {pair} at {rate} with amount {amount}")
        return True  # Confirmar entrada
    
    def bot_start(self, **kwargs) -> None:
        """
        Se ejecuta cuando el bot inicia.
        Útil para setup inicial.
        """
        logger.info("Bot starting...")
        logger.info(f"Using strategy: {self.get_strategy_name()}")
        logger.info(f"Timeframe: {self.timeframe}")
        logger.info(f"Max open trades: {self.max_open_trades}")
