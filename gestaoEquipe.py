import json
import requests
import streamlit as st
import pandas as pd
import os
import mysql.connector
from mysql.connector import Error

config = {
  'host': 'roundhouse.proxy.rlwy.net',
  'user': 'root',
  'port':'26496',
  'password': '2b632BA2FhGFeFb4BHdcdC3G6B6-6-3d',
  'database': 'railway'
}

st.set_page_config(
    page_title="Gestão Equipe",
    layout="wide",
    initial_sidebar_state="expanded"
)

def executa_sql(comando):
    # Conecta ao banco de dados MySQL
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    cursor.execute(comando)
    resultado = cursor.fetchall()
    resultado = pd.DataFrame(resultado)
    resultado.columns = [i[0] for i in cursor.description]
    cursor.close()
    conn.close()
    return resultado

def atualizaBanco(edited_df):
    try:
        # Conecta ao banco de dados MySQL
        conn = mysql.connector.connect(**config)

        if conn.is_connected():
            cursor = conn.cursor()

            table_name = 'Equipe_Completa'

            for _, row in edited_df.iterrows():
                # Verifica se o registro já existe na tabela
                check_query = f"SELECT COUNT(*) FROM {table_name} WHERE Nome_Colaborador = %s"
                cursor.execute(check_query, (row['Nome_Colaborador'],))
                existe = cursor.fetchone()[0]

                if existe:
                    # Atualiza o registro se ele existir
                    update_query = (f"UPDATE {table_name} SET "
                                    "RU = %s, MATRICULA = %s, CARGO = %s, REPORTE = %s, EQUIPE = %s, "
                                    "SIT_ATUAL = %s, DATA_RETORNO = %s WHERE Nome_Colaborador = %s")
                    valores = (row['RU'], row['MATRICULA'], row['CARGO'], row['REPORTE'], row['EQUIPE'],
                               row['SIT_ATUAL'], row['DATA_RETORNO'], row['Nome_Colaborador'])
                    cursor.execute(update_query, valores)
                else:
                    # Insere um novo registro se não existir
                    insert_query = (f"INSERT INTO {table_name} "
                                    "(Nome_Colaborador, RU, MATRICULA, CARGO, REPORTE, EQUIPE, "
                                    "SIT_ATUAL, DATA_RETORNO) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
                    valores = (row['Nome_Colaborador'], row['RU'], row['MATRICULA'], row['CARGO'],
                               row['REPORTE'], row['EQUIPE'], row['SIT_ATUAL'], row['DATA_RETORNO'])
                    cursor.execute(insert_query, valores)

            # Confirma as alterações no banco de dados
            conn.commit()
            st.write(f"Operação concluída na tabela {table_name}.")

    except Error as e:
        st.write(f"Erro: {e}")

    finally:
        # Fecha a conexão ao banco de dados
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def run():
    
    baseCompleta=executa_sql('SELECT * FROM Equipe_Completa')

    # Convertendo colunas para os tipos desejados
    baseCompleta['RU'] = baseCompleta['RU'].astype(str)
    baseCompleta['MATRICULA'] = baseCompleta['MATRICULA'].astype(str).str.replace(".0", "")

    # Filtrando linhas com 'SIT. ATUAL' diferente de 'INATIVOS'
    baseCompleta = baseCompleta.loc[baseCompleta['SIT_ATUAL'] != 'INATIVOS'].reset_index(drop=True)
    # baseCompleta['DATA_RETORNO']=pd.to_datetime(baseCompleta['DATA_RETORNO']).dt.strftime("%d/%m/%Y")

    def exibeEquipe(sit,eqp,rpt):
        if sit == 'TODOS':
            filtro_sit = baseCompleta['SIT_ATUAL'].notnull()  # Qualquer valor diferente de NaN
        else:
            filtro_sit = baseCompleta['SIT_ATUAL'] == sit
        if eqp == 'TODOS':
            filtro_eqp = baseCompleta['EQUIPE'].notnull()  # Qualquer valor diferente de NaN
        else:
            filtro_eqp = baseCompleta['EQUIPE'] == eqp
        if rpt == 'TODOS':
            filtro_rpt = baseCompleta['REPORTE'].notnull()  # Qualquer valor diferente de NaN
        else:
            filtro_rpt = baseCompleta['REPORTE'] == rpt

        DfEqpFiltro=baseCompleta.loc[filtro_sit & filtro_eqp & filtro_rpt].reset_index(drop=True)
        qtdeColabs=len(DfEqpFiltro)
        return DfEqpFiltro,qtdeColabs

    Situacao=['ATIVO','ATESTADO','FÉRIAS','AFASTADO','FALTOU','INATIVO']
    Situacao.insert(0,'TODOS')
    Equipe=list(baseCompleta['EQUIPE'].unique())
    Equipe.insert(0,'TODOS')
    Reporte=list(baseCompleta['REPORTE'].unique())
    Reporte.insert(0,'TODOS')

    col1, col2 = st.columns([1,3])

    with col1:
        optionsSit = st.selectbox(
            'Selecione a Situação desejada',
            Situacao)
        optionsEqp = st.selectbox(
            'Selecione a Equipe',
            Equipe)
        optionsRpt = st.selectbox(
            'Selecione o Resáponsável',
            Reporte)
        DfEqpFiltro,qtdeColabs = exibeEquipe(optionsSit, optionsEqp, optionsRpt)
        qtdAtivos=len(DfEqpFiltro[DfEqpFiltro['SIT_ATUAL']=='ATIVO'])
        dif=qtdAtivos-qtdeColabs
        col1.metric("Total de Colaboradores",qtdeColabs,dif)
        col1.metric("Ativos",value=qtdAtivos)

    with col2:
        edited_df = st.data_editor(DfEqpFiltro,
                                hide_index=True,
                                column_config={
                                    "SIT_ATUAL": st.column_config.SelectboxColumn(
                                        "SIT. ATUAL",
                                        help="Situação do Colaborador",
                                        width="None",
                                        options=['ATIVO','ATESTADO','FÉRIAS','AFASTADO','FALTOU','INATIVO'],
                                        required=True,
                                    )
                                },
                                num_rows="dynamic"
                                )
        atualizar = st.button('ATUALIZAR',type="primary")

    if atualizar:
        atualizaBanco(edited_df)
        st.rerun()

if __name__ == "__main__":
    run()
