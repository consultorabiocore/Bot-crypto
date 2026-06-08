# 📊 Explicación Detallada de la Estrategia Order Flow Breakout

## ¿Qué es Order Flow?

**Order Flow** es el análisis del flujo de órdenes en el mercado:
- Cuando hay más **órdenes de compra** → Presión alcista
- Cuando hay más **órdenes de venta** → Presión bajista

Est estrategia detecta cuándo el flujo cambia, indicando que está por empezar un movimiento fuerte.

---

## Componentes de la Estrategia

### 1️⃣ Order Flow Indicator

```python
order_flow = volumen si (cierre > apertura) else -volumen
