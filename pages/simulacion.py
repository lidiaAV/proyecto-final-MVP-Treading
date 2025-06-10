import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Simulación", layout="wide")
st.title("📊 Simulación de Estrategia en Múltiples Tickers por Año")

if 'dfs_por_ticker' not in st.session_state or not st.session_state.dfs_por_ticker:
    st.warning("Por favor, carga los datos y genera las señales primero.")
    st.stop()

# Sidebar
spread = st.sidebar.number_input("Spread (en puntos)", min_value=0.0, step=0.01, value=0.0, key="spread_sim")
comision = st.sidebar.number_input("Comisión fija (€)", min_value=0.0, step=0.1, value=0.0, key="comision_sim")
capital_inicial = st.sidebar.number_input("Capital inicial (€)", min_value=100.0, step=100.0, value=100.0, key="capital_inicial_sim")

# Cargar y preparar los datos
dfs = []
for ticker, df in st.session_state.dfs_por_ticker.items():
    df = df.copy()
    df['Ticker'] = ticker
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['Señal'] = df['Señal'].astype(str)
    dfs.append(df)

df_total = pd.concat(dfs).sort_values('Fecha').reset_index(drop=True)

# Selección de año
años_disponibles = sorted(df_total['Fecha'].dt.year.unique(), reverse=True)
año_seleccionado = st.selectbox("Selecciona el año de simulación", años_disponibles)

df_total_anual = df_total[df_total['Fecha'].dt.year == año_seleccionado]

todas_fechas = pd.date_range(df_total_anual['Fecha'].min(), df_total_anual['Fecha'].max(), freq='D')
tabla_inversiones = pd.DataFrame({'Fecha': todas_fechas})

resultados_estrategia = {}
resultados_hold = {}
rentabilidades_por_ticker = []

for ticker in st.session_state.dfs_por_ticker:
    df = df_total_anual[df_total_anual['Ticker'] == ticker].copy().sort_values('Fecha')

    capital = capital_inicial
    en_posicion = False
    precio_compra = 0
    capital_por_fecha = []

    for fecha in todas_fechas:
        fila = df[df['Fecha'] == fecha]
        if not fila.empty:
            señal = fila.iloc[0]['Señal']
            precio = fila.iloc[0]['Último']

            if not en_posicion and señal == '📈 Comprar':
                precio_compra = precio + spread
                capital -= comision
                en_posicion = True

            elif en_posicion and señal == '📉 Vender':
                precio_venta = precio
                beneficio = (precio_venta - precio_compra) / precio_compra * capital
                capital += beneficio - comision
                en_posicion = False

        capital_por_fecha.append(capital if en_posicion else 0)

    tabla_inversiones[ticker] = capital_por_fecha
    resultados_estrategia[ticker] = round(capital, 2)

    # Calcular Buy & Hold
    df_hold = df[df['Fecha'].isin(todas_fechas)]
    if len(df_hold) >= 2:
        precio_inicio = df_hold.iloc[0]['Último']
        precio_fin = df_hold.iloc[-1]['Último']
        ganancia_pct = (precio_fin - precio_inicio) / precio_inicio
        resultado_hold = capital_inicial * (1 + ganancia_pct) - 2 * comision
        resultados_hold[ticker] = round(resultado_hold, 2)
    else:
        resultados_hold[ticker] = None

# ➕ Agregar columna Total Invertido
tabla_inversiones['Total Invertido'] = tabla_inversiones.drop(columns='Fecha').sum(axis=1)

st.subheader("📅 Evolución de Inversión Diaria por Ticker y Total")
st.dataframe(tabla_inversiones)

# 🔍 Días sin ninguna inversión
dias_sin_inversion = tabla_inversiones[tabla_inversiones['Total Invertido'] == 0]
st.warning(f"🔍 Días sin ninguna inversión: {len(dias_sin_inversion)}")

# 📊 Resultados finales por ticker
st.subheader(f"📊 Resultado final por ticker ({año_seleccionado}) - Estrategia")
total_estrategia = 0
for ticker, valor_final in resultados_estrategia.items():
    total_estrategia += valor_final
    st.markdown(f"- **{ticker}**: {valor_final:.2f} €")
st.markdown(f"✅ **Total acumulado estrategia:** `{total_estrategia:.2f} €`")

# 💼 Comparativa Buy & Hold
st.subheader("💼 Comparativa Buy & Hold")
total_hold = 0
for ticker, resultado in resultados_hold.items():
    if resultado is not None:
        total_hold += resultado
        st.markdown(f"- **{ticker}**: Buy & Hold → {resultado:.2f} €")
st.markdown(f"📈 **Total acumulado Buy & Hold:** `{total_hold:.2f} €`")

# 📈 Media diaria invertida
media_anual = tabla_inversiones['Total Invertido'].mean()
st.subheader(f"📈 Media diaria de dinero invertido en {año_seleccionado}: `{media_anual:.2f} €`")

# 📉 Gráfico de inversión diaria
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(tabla_inversiones['Fecha'], tabla_inversiones['Total Invertido'], color='blue')
ax.set_title("Capital Total Invertido por Día")
ax.set_xlabel("Fecha")
ax.set_ylabel("€ Invertidos")
st.pyplot(fig)

# 📈 Rentabilidad Media Anual (%): Estrategia vs Buy & Hold
st.subheader("📈 Rentabilidad Media Anual Comparada (%)")
rentabilidades_estrategia = []
rentabilidades_hold = []
rentabilidades_tickers = []

for ticker in st.session_state.dfs_por_ticker:
    df = df_total_anual[df_total_anual['Ticker'] == ticker].copy()
    if df.empty or len(df) < 2:
        continue

    capital_final_estrategia = resultados_estrategia.get(ticker, capital_inicial)
    resultado_hold = resultados_hold.get(ticker)

    r_estrategia = 100 * (capital_final_estrategia / capital_inicial - 1)
    r_hold = 100 * (resultado_hold / capital_inicial - 1) if resultado_hold else 0

    rentabilidades_estrategia.append(r_estrategia)
    rentabilidades_hold.append(r_hold)

    rentabilidades_tickers.append({
        "Ticker": ticker,
        "Estrategia (%)": r_estrategia,
        "Buy & Hold (%)": r_hold
    })

media_estrategia_pct = round(sum(rentabilidades_estrategia) / len(rentabilidades_estrategia), 2) if rentabilidades_estrategia else 0
media_hold_pct = round(sum(rentabilidades_hold) / len(rentabilidades_hold), 2) if rentabilidades_hold else 0

st.markdown(f"- 📊 **Estrategia**: `{media_estrategia_pct}% anual`")
st.markdown(f"- 💼 **Buy & Hold**: `{media_hold_pct}% anual`")

# 📊 Gráfico de barras comparando rentabilidades
df_rent = pd.DataFrame(rentabilidades_tickers)
df_rent = df_rent.set_index("Ticker")

st.subheader("📊 Rentabilidad por Ticker (%)")
fig2, ax2 = plt.subplots(figsize=(10, 5))
df_rent.plot(kind='bar', ax=ax2)
ax2.set_ylabel("Rentabilidad (%)")
ax2.set_title("Comparativa Rentabilidad por Ticker")
st.pyplot(fig2)

# 📆 Rentabilidad media últimos 3 años
st.subheader("📆 Rentabilidad Media de los Últimos 3 Años (%)")
ultimos_tres_anios = años_disponibles[:3]
rentabilidades_estrategia_3y = []
rentabilidades_hold_3y = []

for ticker in st.session_state.dfs_por_ticker:
    r_estrategia_total = 0
    r_hold_total = 0
    años_validos = 0

    for anio in ultimos_tres_anios:
        df_anual = df_total[df_total['Fecha'].dt.year == anio]
        df_ticker = df_anual[df_anual['Ticker'] == ticker]

        if df_ticker.empty or len(df_ticker) < 2:
            continue

        precio_inicio = df_ticker.iloc[0]['Último']
        precio_fin = df_ticker.iloc[-1]['Último']
        r_hold = 100 * (precio_fin - precio_inicio) / precio_inicio

        capital = capital_inicial
        en_posicion = False
        precio_compra = 0

        fechas = pd.date_range(df_ticker['Fecha'].min(), df_ticker['Fecha'].max(), freq='D')

        for fecha in fechas:
            fila = df_ticker[df_ticker['Fecha'] == fecha]
            if not fila.empty:
                señal = fila.iloc[0]['Señal']
                precio = fila.iloc[0]['Último']

                if not en_posicion and señal == '📈 Comprar':
                    precio_compra = precio + spread
                    capital -= comision
                    en_posicion = True

                elif en_posicion and señal == '📉 Vender':
                    precio_venta = precio
                    beneficio = (precio_venta - precio_compra) / precio_compra * capital
                    capital += beneficio - comision
                    en_posicion = False

        r_estrategia = 100 * (capital / capital_inicial - 1)

        r_estrategia_total += r_estrategia
        r_hold_total += r_hold
        años_validos += 1

    if años_validos > 0:
        rentabilidades_estrategia_3y.append(r_estrategia_total / años_validos)
        rentabilidades_hold_3y.append(r_hold_total / años_validos)

media_estrategia_3y = round(sum(rentabilidades_estrategia_3y) / len(rentabilidades_estrategia_3y), 2) if rentabilidades_estrategia_3y else 0.0
media_hold_3y = round(sum(rentabilidades_hold_3y) / len(rentabilidades_hold_3y), 2) if rentabilidades_hold_3y else 0.0

st.markdown(f"- 📊 **Estrategia**: `{media_estrategia_3y}% media últimos 3 años`")
st.markdown(f"- 💼 **Buy & Hold**: `{media_hold_3y}% media últimos 3 años`")

# 🔁 Botón de reinicio
if st.button("❌ Quitar archivo cargado y reiniciar"):
    st.session_state.df = None
    st.session_state.dfs_por_ticker = {}
    st.rerun()
