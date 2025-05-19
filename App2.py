import streamlit as st
import pandas as pd
import numpy as np
import openpyxl

def transformar_data(df):
    columnas = [
    "SINIESTRO", "VEHICULO", "DM", "RC","RT",
    "SINTOTAL", "ESTADO", "CAUSA", "SERIE","MODELO","PT","FECHA"
    ]

    data_filtrado = df[columnas].copy()

    # Transformar PT a numérico y luego mapear "PT" a 1 y otros a 0
    data_filtrado["PT"] = data_filtrado["PT"].fillna(0)
    data_filtrado['PT'] = data_filtrado['PT'].apply(lambda x: 1 if x == "PT" else 0)

    # Transformar FECOCU a fecha
    data_filtrado["FECHA_NUM"] = pd.to_numeric(data_filtrado["FECHA"], errors= "coerce")
    data_filtrado["FECHA_FIN"] = pd.to_datetime(data_filtrado["FECHA_NUM"], unit="D", origin="1899-12-30")  # sin unit ni origin
    data_filtrado = data_filtrado.drop(["FECHA", "FECHA_NUM"], axis=1)

    # Convertir columnas numéricas
    cols_numericas = ["PT", "SINTOTAL","DM","RC","RT"]
    for col in cols_numericas:
        data_filtrado[col] = pd.to_numeric(data_filtrado[col], errors='coerce')

    duplicados = data_filtrado[data_filtrado.duplicated(subset=["SINIESTRO"], keep=False)]

    if not duplicados.empty:
        print(f"Hay {duplicados['SINIESTRO'].nunique()} valores duplicados en SINIESTRO.\n")
        print("Ejemplos de duplicados:")
        print(duplicados.sort_values("SINIESTRO").head(10))
    else:
        print("No hay duplicados en SINIESTRO.")

    # Ordena de mayor a menor según SINTOTAL para que el más grande quede primero
    data_filtrado = data_filtrado.sort_values(by="SINTOTAL", ascending=False)

    # Luego elimina duplicados quedándote con la primera ocurrencia (la mayor SINTOTAL)
    data_filtrado = data_filtrado.drop_duplicates(subset=["SINIESTRO"], keep='first')

        # CREAR COLUMNA PARA DIFERENCIA DE MONTO
    data_filtrado['DIF_MONTO'] = data_filtrado["DM"] - data_filtrado["RC"]

    # filtro vacíos
    data_filtrado['COBERTURA'] = ""

    # ASISTENCIA VIAL POR NOMBRE
    mask = (data_filtrado['CAUSA'] == "ASISTENCIA VIAL") & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "Asistencia"

    # MONTO DE ROBO MAYOR A 0 = "RT"
    mask = (data_filtrado["RT"] > 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "RT"

    # SINIESTROS ENTRE -700 Y 700 = "Asistencia"
    mask = (data_filtrado['SINTOTAL'].between(-700, 700)) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "Asistencia"

    # SI DIFERENCIA MONTO > 0 = "DM"
    mask = (data_filtrado['DIF_MONTO'] > 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "DM"

    # 3. SI DIFERENCIA MONTO < 0 = "RC"
    mask = (data_filtrado['DIF_MONTO'] < 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "RC"

    # 6. SINTOTAL > -700 = "DM"
    mask = (data_filtrado['SINTOTAL'] < 0) & (data_filtrado['COBERTURA'] == "")
    data_filtrado.loc[mask, 'COBERTURA'] = "DM"

    # 7. Faltantes (monto en SINTOTAL pero sin diferencia entre DM y RC)
    mask = (
        (data_filtrado['SINTOTAL'] > 0) &
        (data_filtrado['DIF_MONTO'] == 0) &
        (data_filtrado['COBERTURA'] == "")
    )
    data_filtrado.loc[mask, 'COBERTURA'] = "FALTANTE"

    data_filtrado["PT"] = np.where(
        (data_filtrado["PT"] == "PT") | (data_filtrado["RT"] > 100000),
        1,
        0
    )

    #VERIFICAR VACÍOS Y NAN EN "COBERTURA"
    num_vacios = (data_filtrado['COBERTURA'] == "").sum()

    num_nan = data_filtrado['COBERTURA'].isna().sum()

    print(f"Filas con COBERTURA vacía: {num_vacios}")
    print(f"Filas con COBERTURA NaN: {num_nan}")

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
