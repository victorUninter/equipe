from openpyxl import load_workbook
from streamlit.logger import get_logger
from git.exc import GitCommandError
from datetime import datetime
from datetime import date
import streamlit as st
from streamlit.connections import SQLConnection
import datetime as dt
from git import Repo
import pandas as pd 
import sqlite3
import time
import sys
import os
import re

st.set_page_config(
    page_title="Gestão Equipe",
    # page_icon=,
    layout="wide",
    initial_sidebar_state="expanded"
)
col1,col2,col3=st.columns([2,5,1])
with col1:
    st.image("marca-uninter-horizontal.png", use_column_width=True)
with col2:
    st.title('Gestão Equipe de Cobrança')

LOGGER = get_logger(__name__)

os.system("eval $(ssh-agent -s)")
os.system("ssh-add ~/.ssh/id_rsa")

def atualizaBase(con,edited_df,baseCompleta):
    # Garanta que o índice de 'edited_df' seja exclusivo
    edited_df = edited_df.drop_duplicates(subset='Nome_Colaborador').reset_index(drop=True)

    # Crie uma cópia da baseCompleta filtrada
    base_filtrada_copy = baseCompleta.loc[baseCompleta['Nome_Colaborador'].isin(edited_df['Nome_Colaborador'])].copy()

    for i, col in enumerate(edited_df.columns):
        if i > 0:
            # Atualize apenas a cópia filtrada
            base_filtrada_copy[col] = base_filtrada_copy['Nome_Colaborador'].map(
                edited_df.set_index('Nome_Colaborador')[col])

    # Combine as informações atualizadas de volta à baseCompleta
    baseCompleta.update(base_filtrada_copy, overwrite=True)

    # Garanta que o índice de 'baseCompleta' seja exclusivo antes de salvar no SQL
    baseCompleta = baseCompleta.drop_duplicates(subset='Nome_Colaborador').reset_index(drop=True)

    # Salve no SQL
    baseCompleta.to_sql('Equipe_Completa', con, index=False, if_exists='replace')

def auto_commit(git_token):
    try:
        # Certifique-se de estar no diretório correto
        caminho = os.path.dirname(os.path.abspath(__file__))
        os.chdir(caminho)

        # Inicializa o repositório Git
        repo = Repo('.')

        # URL do repositório com o token
        repo_url = f"https://victorUninter:{git_token}@github.com/victorUninter/equipe.git"

        # Verifica se há alterações para commitar
        if repo.is_dirty(untracked_files=True):
            # Adiciona todas as alterações ao staging
            repo.git.add(all=True)

            # Faz o commit com uma mensagem automática
            repo.git.commit(m="Atualizando banco de dados")

            # Empurra as alterações para o repositório remoto (substitua 'main' pelo nome do seu branch)
            repo.git.push(repo_url, 'main')

            st.success("Git push executado com sucesso.")
        else:
            st.warning("Nenhuma alteração para commitar.")
    except GitCommandError as git_error:
        st.error(f"Erro ao realizar commits automáticos: {git_error}")
    except Exception as e:
        st.error(f"Erro desconhecido: {e}")
         
def run():
    st.write("Diretório de trabalho atual:", os.getcwd())
    caminho_Banco = "BDEquipe.db"
    con = sqlite3.connect(caminho_Banco)
    cur = con.cursor()

    # novabase=pd.read_excel('EQUIPE COB E TELE.xlsm')
    # novabase=novabase.iloc[:,:8]
    # novabase.to_sql('Equipe_Completa', con, index=False, if_exists='replace')

    @st.cache_resource
    def executa_sql(comando):
        cur.execute(comando)
        resultado = cur.fetchall()
        resultado = pd.DataFrame(resultado)
        resultado.columns = [i[0] for i in cur.description]
        print(resultado.shape)
        return resultado

    baseCompleta=executa_sql('SELECT * FROM Equipe_Completa')
    baseCompleta['RU']=baseCompleta['RU'].astype(str)
    baseCompleta['MATRICULA']=baseCompleta['MATRICULA'].astype(str).str.replace(".0","")
    baseCompleta=baseCompleta.loc[baseCompleta['SIT. ATUAL']!='INATIVOS']
    # baseCompleta['DATA_RETORNO']=pd.to_datetime(baseCompleta['DATA_RETORNO']).dt.strftime("%d/%m/%Y")

    @st.cache_resource
    def exibeEquipe(sit,eqp,rpt):
        if sit == 'TODOS':
            filtro_sit = baseCompleta['SIT. ATUAL'].notnull()  # Qualquer valor diferente de NaN
        else:
            filtro_sit = baseCompleta['SIT. ATUAL'] == sit
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

    Situacao=['ATIVO','ATESTADO','FÉRIAS','AFASTADO','FALTOU']
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
        qtdAtivos=len(DfEqpFiltro[DfEqpFiltro['SIT. ATUAL']=='ATIVO'])
        dif=qtdAtivos-qtdeColabs
        col1.metric("Total de Colaboradores",qtdeColabs,dif)
        col1.metric("Ativos",value=qtdAtivos)

    with col2:
        edited_df = st.data_editor(DfEqpFiltro,
                                hide_index=True,
                                column_config={
                                    "SIT. ATUAL": st.column_config.SelectboxColumn(
                                        "SIT. ATUAL",
                                        help="Situação do Colaborador",
                                        width="None",
                                        options=['ATIVO','ATESTADO','FÉRIAS','AFASTADO','FALTOU'],
                                        required=True,
                                    )
                                },
                                num_rows="dynamic"
                                )
        atualizar = st.button('ATUALIZAR',type="primary")

    if atualizar:
        atualizaBase(con,edited_df,baseCompleta)
        st.rerun()

    con.close()

if __name__ == "__main__":
    run()
    git_token="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"
    auto_commit(git_token)
