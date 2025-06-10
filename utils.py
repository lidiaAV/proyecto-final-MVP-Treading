import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def ruta_modelo(ticker, fecha):
    carpeta = os.path.join("models_reentrenar", ticker)
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, f"{fecha}.pkl")

def cargar_modelo_si_existe(ticker, fecha):
    ruta = ruta_modelo(ticker, fecha)
    if os.path.exists(ruta):
        return joblib.load(ruta)
    return None

def guardar_modelo(modelo, ticker, fecha):
    ruta = ruta_modelo(ticker, fecha)
    joblib.dump(modelo, ruta)

def calcular_rsi(df, window=5):
    delta = df['Último'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_features(df):
    df['RSI'] = calcular_rsi(df)
    df['MA5'] = df['Último'].rolling(window=5).mean()
    df['MA10'] = df['Último'].rolling(window=10).mean()
    df['Retorno'] = df['Último'].pct_change()
    df['Volatilidad'] = df['Retorno'].rolling(window=5).std()
    df['Momentum'] = df['Último'] - df['Último'].shift(5)

    # === Bandas de Bollinger ===
    window = 20
    df['SMA'] = df['Último'].rolling(window=window).mean()
    df['std'] = df['Último'].rolling(window=window).std()
    df['Bollinger_Upper'] = df['SMA'] + 2 * df['std']
    df['Bollinger_Lower'] = df['SMA'] - 2 * df['std']
    df['Bollinger_Width'] = df['Bollinger_Upper'] - df['Bollinger_Lower']
    df['Dist_Upper'] = df['Bollinger_Upper'] - df['Último']
    df['Dist_Lower'] = df['Último'] - df['Bollinger_Lower']

    return df

def walk_forward_predicciones(df_t, spread, ticker, reentrenar=False):
    df_t = df_t.sort_values('Fecha').copy()

    # Calcular indicadores
    df_t = calcular_features(df_t)
    horizon = 5
    df_t['Target'] = ((df_t['Último'].shift(-horizon) - (df_t['Último'] + spread)) > 0).astype(int)
    df_t.dropna(subset=['RSI', 'Vol.', 'Target'], inplace=True)

    predicciones = []
    fechas_validas = df_t['Fecha'].dt.date.unique()

    features = [
        'RSI', 'Vol.', 'Momentum',
        'Bollinger_Width', 'Dist_Upper', 'Dist_Lower'
    ]

    for fecha in fechas_validas:
        fecha_str = fecha.strftime("%Y-%m-%d")
        modelo = None
        if not reentrenar:
            modelo = cargar_modelo_si_existe(ticker, fecha_str)

        if modelo is None:
            fin_entrenamiento = pd.to_datetime(fecha) - pd.Timedelta(days=1)
            inicio_entrenamiento = fin_entrenamiento - pd.DateOffset(years=3)
            df_train = df_t[(df_t['Fecha'] >= inicio_entrenamiento) & (df_t['Fecha'] <= fin_entrenamiento)].copy()
            if len(df_train) < 50:
                continue

            X_train = df_train[features].dropna()
            y_train = df_train.loc[X_train.index, 'Target']

            modelo = RandomForestClassifier(n_estimators=100, random_state=42)
            modelo.fit(X_train, y_train)
            guardar_modelo(modelo, ticker, fecha_str)

        df_pred = df_t[df_t['Fecha'].dt.date == fecha].copy()
        if df_pred.empty:
            continue

        X_pred = df_pred[features].dropna()
        if X_pred.empty:
            continue

        df_pred = df_pred.loc[X_pred.index]
        df_pred['Predicción'] = modelo.predict(X_pred)
        df_pred['Señal'] = df_pred['Predicción'].apply(lambda x: '📈 Comprar' if x == 1 else '📉 Vender')
        predicciones.append(df_pred)

    if predicciones:
        return pd.concat(predicciones).reset_index(drop=True)
    else:
        return pd.DataFrame()
