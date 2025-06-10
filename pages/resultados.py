import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import walk_forward_predicciones
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
st.set_page_config(page_title="Resultados", layout="wide")
st.title("📊 Resultados de hoy")

spread = st.sidebar.number_input("Spread (en puntos)", min_value=0.0, value=0.0, step=0.01, key="spread_input")
comision = st.sidebar.number_input("Comisión fija (en €)", min_value=0.0, value=0.0, step=0.1, key="comision_input")
reentrenar = st.sidebar.checkbox("🔁 Reentrenar modelos aunque ya existan", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Costes aplicados")
st.sidebar.markdown(f"- Spread actual: `{spread}` puntos")
st.sidebar.markdown(f"- Comisión actual: `{comision} €`")

if "df" not in st.session_state or st.session_state.df is None:
    st.warning("🔁 Carga los datos desde la página principal primero.")
    st.stop()

df = st.session_state.df.copy()

# Contenedor para resultados por ticker
if "dfs_por_ticker" not in st.session_state:
    st.session_state.dfs_por_ticker = {}

if "Ticker" in df.columns:
    st.subheader("📋 Resumen de señales de hoy por activo")
    resumen = []

    for ticker in df["Ticker"].unique():
        df_t = df[df["Ticker"] == ticker].copy()

        df_pred = walk_forward_predicciones(df_t, spread, ticker, reentrenar=reentrenar)
        if df_pred.empty:
            st.warning(f"No se pudieron generar predicciones para {ticker}")
            continue

        st.session_state.dfs_por_ticker[ticker] = df_pred

        ultima = df_pred.iloc[-1]

        resumen.append({
            "Ticker": ticker,
            "Fecha": ultima["Fecha"].date(),
            "Precio": round(ultima["Último"], 2),
            "RSI": round(ultima["RSI"], 2),
            "Volumen": round(ultima["Vol."], 0),
            "Señal": ultima["Señal"]
        })

    if resumen:
        df_resumen = pd.DataFrame(resumen)
        st.dataframe(df_resumen)

        resumen_csv = df_resumen.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar resumen de señales", resumen_csv, "resumen_senales.csv", "text/csv")

        ticker_sel = st.selectbox("Selecciona un activo para análisis detallado:", df_resumen["Ticker"])
        df = st.session_state.dfs_por_ticker[ticker_sel]
    else:
        st.warning("No se pudieron generar señales para ningún activo.")
        st.stop()

else:
    st.subheader("📋 Resumen de señales de hoy (único activo)")
    ticker = "_único"

    df_pred = walk_forward_predicciones(df, spread, ticker, reentrenar=reentrenar)
    if df_pred.empty:
        st.warning("No se pudieron generar predicciones para este activo.")
        st.stop()

    st.session_state.dfs_por_ticker = {ticker: df_pred}
    df = df_pred

    ultima = df.iloc[-1]
    resumen = {
        "Fecha": ultima["Fecha"].date(),
        "Precio": round(ultima["Último"], 2),
        "RSI": round(ultima["RSI"], 2),
        "Volumen": round(ultima["Vol."], 0),
        "Señal": ultima["Señal"]
    }
    st.dataframe(pd.DataFrame([resumen]))

# === Visualización detallada ===
st.markdown("## 📌 Señal para hoy")

dias = st.slider("¿Cuántos días mostrar?", 30, 180, 90)
df_viz = df.tail(dias)

fig, ax1 = plt.subplots(figsize=(12, 5))
line1, = ax1.plot(df_viz['Fecha'], df_viz['RSI'], color='blue', label='RSI')
ax1.axhline(70, color='red', linestyle='--')
ax1.axhline(30, color='green', linestyle='--')
ax1.set_ylabel('RSI')

ax2 = ax1.twinx()
line2, = ax2.plot(df_viz['Fecha'], df_viz['Último'], color='orange', label='Precio')
ax2.set_ylabel('Precio')

ax1.legend([line1, line2], ['RSI', 'Precio'], loc='upper left')
st.pyplot(fig)

st.subheader("🔮 Señales recientes")
st.dataframe(df[['Fecha', 'Último', 'RSI', 'Vol.', 'Predicción', 'Señal']].tail(10))

csv_out = df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Descargar CSV del activo", csv_out, "predicciones.csv", "text/csv")

if 'Target' in df.columns and 'Predicción' in df.columns:
    y_true = df['Target']
    y_pred = df['Predicción']

    if len(set(y_true)) >= 2:
        cm = confusion_matrix(y_true, y_pred)
        fig_cm, ax_cm = plt.subplots()
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=['Vender', 'Comprar'],
                    yticklabels=['Vender', 'Comprar'], ax=ax_cm)
        ax_cm.set_xlabel('Predicción')
        ax_cm.set_ylabel('Real')
        ax_cm.set_title('Matriz de Confusión')
        st.pyplot(fig_cm)

        report = classification_report(y_true, y_pred, target_names=['Vender', 'Comprar'], output_dict=True)
        df_metrics = pd.DataFrame(report).transpose().round(2)
        st.dataframe(df_metrics)
    else:
        st.info("No hay suficientes clases para generar la matriz de confusión.")
else:
    st.info("No hay columnas de 'Target' o 'Predicción' para evaluar el modelo.")