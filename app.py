import streamlit as st
import pandas as pd
import yfinance as yf
import time

st.set_page_config(page_title="Carga de datos", layout="wide")
st.title("📥 Carga de datos")


# === Reinicio de datos previos ===
if st.session_state.get("df") is not None:
    if st.button("❌ Quitar archivo cargado y reiniciar"):
        st.session_state.df = None
        st.rerun()

# === Diccionario de índices ===
indices = {
    "DAX": [
        "ADS.DE",   # Adidas
        "AIR.DE",   # Airbus
        "ALV.DE",   # Allianz
        "BAS.DE",   # BASF
        "BAYN.DE",  # Bayer
        "BEI.DE",   # Beiersdorf
        "BMW.DE",   # BMW
        "BNR.DE",   # Brenntag
        "CBK.DE",   # Commerzbank
        "CON.DE",   # Continental
        "1COV.DE",  # Covestro
        "DTG.DE",   # Daimler Truck
        "DBK.DE",   # Deutsche Bank
        "DB1.DE",   # Deutsche Börse
        "DHL.DE",   # Deutsche Post
        "DTE.DE",   # Deutsche Telekom
        "EOAN.DE",  # E.ON
        "FRE.DE",   # Fresenius
        "FME.DE",   # Fresenius Medical Care
        "HNR1.DE",  # Hannover Rück
        "HEI.DE",   # Heidelberg Materials
        "HEN3.DE",  # Henkel
        "IFX.DE",   # Infineon Technologies
        "MBG.DE",   # Mercedes-Benz Group
        "MRK.DE",   # Merck
        "MTX.DE",   # MTU Aero Engines
        "MUV2.DE",  # Münchener Rück
        "PAH3.DE",  # Porsche Automobil Holding
        "P911.DE",  # Porsche AG
        "QIA.DE",   # Qiagen
        "RHM.DE",   # Rheinmetall
        "RWE.DE",   # RWE
        "SAP.DE",   # SAP
        "SRT3.DE"   # Sartorius

    ],
    "IBEX 35": [
        "ACS.MC", "AENA.MC", "AMS.MC", "ANA.MC", "BBVA.MC", "BKT.MC",
        "CABK.MC", "CLNX.MC", "COL.MC", "ENG.MC", "FER.MC", "GRF.MC",
        "IAG.MC", "IBE.MC", "ITX.MC", "MAP.MC", "MEL.MC", "MRL.MC",
        "NTGY.MC", "PHM.MC", "RED.MC", "REP.MC", "ROVI.MC", "SAB.MC",
        "SAN.MC", "SGRE.MC", "SLR.MC", "SOL.MC", "TEF.MC", "VIS.MC",
        "LOG.MC", "EBRO.MC", "ENAG.MC", "ACC.MC", "ALM.MC"
    ]
}

# === Selección de fuente ===
st.subheader("📂 Selecciona la fuente de datos")
fuente = st.radio("Fuente:", ["📤 Subir archivo CSV", "🌐 Yahoo Finance - Individual", "🌐 Yahoo Finance - Índice"])

df = None

# === Opción 1: Carga de CSV ===
if fuente == "📤 Subir archivo CSV":
    archivo = st.file_uploader("Carga tu archivo CSV", type=["csv"])
    if archivo:
        df = pd.read_csv(archivo, decimal=',', thousands='.')
        df['Fecha'] = df['Fecha'].astype(str).str.zfill(8)
        df['Fecha'] = df['Fecha'].str.replace(r'(\d{2})(\d{2})(\d{4})', r'\1/\2/\3', regex=True)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
        df = df.sort_values(by='Fecha').reset_index(drop=True)
        df['Dia_semana'] = df['Fecha'].dt.day_name()

        df['Vol.'] = df['Vol.'].astype(str).replace(['nan', 'None', ''], '0')
        df['Vol.'] = df['Vol.'].apply(lambda x: float(x.replace(',', '.').replace('M', 'e6')
                                                       .replace('K', 'e3').replace('B', 'e9')
                                                       .replace('T', 'e12')) if x else 0)
        nombre_archivo = archivo.name.replace(".csv", "")
        df['Ticker'] = nombre_archivo.upper()
        st.session_state.df = df
        st.success("✅ Datos cargados correctamente.")
        st.switch_page("pages/resultados.py")

# === Opción 2: Yahoo Finance individual ===
elif fuente == "🌐 Yahoo Finance - Individual":
    ticker = st.text_input("Introduce el ticker (ej: AAPL, SAN.MC):", "SAN.MC")
    periodo = st.selectbox("Periodo:", ["2y", "5y", "10y"])
    intervalo = st.selectbox("Intervalo:", ["1d", "1wk", "1mo"])
    if st.button("📥 Descargar datos del ticker"):
        data = yf.download(ticker, period=periodo, interval=intervalo)
        if data.empty:
            st.error("No se encontraron datos.")
            st.stop()
        data.reset_index(inplace=True)

        # Aplanar MultiIndex si existe
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [' '.join(col).strip() for col in data.columns.values]

        close_col = [col for col in data.columns if 'Close' in col]
        vol_col = [col for col in data.columns if 'Volume' in col]

        if not close_col or not vol_col:
            st.error("❌ El dataset no contiene columnas de cierre o volumen.")
            st.stop()

        data.rename(columns={close_col[0]: 'Último', vol_col[0]: 'Vol.'}, inplace=True)
        data.rename(columns={'Date': 'Fecha'}, inplace=True)

        df = data[['Fecha', 'Último', 'Vol.']].copy()
        df["Ticker"] = ticker
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['Dia_semana'] = df['Fecha'].dt.day_name()
        st.session_state.df = df
        st.success("✅ Datos descargados correctamente.")
        st.switch_page("pages/resultados.py")

# === Opción 3: Yahoo Finance por índice ===
elif fuente == "🌐 Yahoo Finance - Índice":
    indice = st.selectbox("Selecciona un índice:", list(indices.keys()))
    periodo = st.selectbox("Periodo:", ["2y", "5y", "10y"])
    intervalo = st.selectbox("Intervalo:", ["1d", "1wk", "1mo"])

    if st.button("📥 Descargar datos del índice"):
        tickers = indices[indice]
        all_data = []

        for ticker in tickers:
            try:
                st.write(f"Descargando: {ticker}")
                data = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
                time.sleep(1.5)  # Espera para evitar baneos

                if not data.empty:
                    df_ticker = data.reset_index()[["Date", "Close", "Volume"]].copy()
                    df_ticker.columns = ["Fecha", "Último", "Vol."]
                    df_ticker["Ticker"] = ticker
                    all_data.append(df_ticker)
            except Exception as e:
                st.warning(f"⚠️ Error con {ticker}: {e}")

        if all_data:
            df_final = pd.concat(all_data, ignore_index=True)
            df_final['Fecha'] = pd.to_datetime(df_final['Fecha'])
            df_final['Dia_semana'] = df_final['Fecha'].dt.day_name()
            
            # Guardar en df global
            st.session_state.df = df_final

            # 👉 Separar por ticker y guardarlos también en dfs_por_ticker
            dfs_por_ticker = {}
            for ticker in df_final['Ticker'].unique():
                dfs_por_ticker[ticker] = df_final[df_final['Ticker'] == ticker].copy()
            st.session_state.dfs_por_ticker = dfs_por_ticker
            
            st.success("✅ Datos descargados correctamente.")
            st.dataframe(df_final.tail(10))
            st.switch_page("pages/resultados.py")
        else:
            st.error("❌ No se pudieron descargar datos para ningún ticker.")
