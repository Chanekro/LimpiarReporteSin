import streamlit as st
import pandas as pd
import numpy as np

def transformar_data(df):
    columnas = [
        "CVESTRO", "VEHICULO", "SINOCUDM", "SINOCURC",
        "SINTOTAL", "ESTADO_SIN", "CAUSA", "SERIE", "PT", "MOD", "FECOCU", "SINOCURT"
    ]

    data_filtrado = df[columnas].copy()

    # Transformar PT a numérico y luego mapear "PT" a 1 y otros a 0
    data_filtrado['PT'] = data_filtrado['PT'].fillna(0)
    data_filtrado['PT'] = data_filtrado['PT'].apply(lambda x: 1 if x == "PT" else 0)

    # Transformar FECOCU a fecha
    data_filtrado["FECOCU_num"] = pd.to_numeric(data_filtrado["FECOCU"], errors="coerce")
    data_filtrado["FECHA"] = pd.to_datetime(data_filtrado["FECOCU_num"], unit="D", origin="1899-12-30")
    data_filtrado = data_filtrado.drop(columns=['FECOCU', 'FECOCU_num'])

    # Convertir columnas numéricas
    cols_numericas = ['PT', 'SINTOTAL', 'SINOCUDM', "SINOCURC", "SINOCURT"]
    for col in cols_numericas:
        data_filtrado[col] = pd.to_numeric(data_filtrado[col], errors='coerce')

    # Ordenar por SINTOTAL descendente y eliminar duplicados por CVESTRO
    data_filtrado = data_filtrado.sort_values(by='SINTOTAL', ascending=False)
    data_filtrado = data_filtrado.drop_duplicates(subset=['CVESTRO'], keep='first')

    # Calcular diferencia monto
    data_filtrado['DIF_MONTO'] = data_filtrado['SINOCUDM'] - data_filtrado['SINOCURC']

    # Crear columna COBERTURA vacía
    data_filtrado['COBERTURA'] = ""

    # Aplicar reglas para COBERTURA
    mask = (data_filtrado['CAUSA'] == "ASISTENCIA VIAL") & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "Asistencia"

    mask = (data_filtrado['SINOCURT'] > 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "RT"

    mask = (data_filtrado['SINTOTAL'].between(-700, 700)) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "Asistencia"

    mask = (data_filtrado['DIF_MONTO'] > 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "DM"

    mask = (data_filtrado['DIF_MONTO'] < 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "RC"

    mask = (data_filtrado['SINTOTAL'] < 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "DM"

    mask = (
        (data_filtrado['SINTOTAL'] > 0) &
        (data_filtrado['DIF_MONTO'] == 0) &
        (data_filtrado['COBERTURA'] == "")
    )
    data_filtrado.loc[mask, 'COBERTURA'] = "FALTANTE"

    # Ajustar PT de nuevo según regla
    data_filtrado['PT'] = np.where(
        (data_filtrado['PT'] == 1) | (data_filtrado['SINOCURT'] > 100000),
        1,
        0
    )

    # Estadísticas para debug (se pueden mostrar en la app)
    num_vacios = (data_filtrado['COBERTURA'] == "").sum()
    num_nan = data_filtrado['COBERTURA'].isna().sum()

    st.write(f"Filas con COBERTURA vacía: {num_vacios}")
    st.write(f"Filas con COBERTURA NaN: {num_nan}")

    return data_filtrado

st.title("Transformación de siniestralidad")

uploaded_file = st.file_uploader("Carga tu archivo Excel", type=["xlsx", "xls"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    resultado = transformar_data(df)
    st.dataframe(resultado)

    # Botón para descargar el resultado transformado
    @st.cache_data
    def to_excel(df):
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()


    excel_data = to_excel(resultado)
    st.download_button(
        label="Descargar Excel transformado",
        data=excel_data,
        file_name="siniestralidad_transformada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
