import json
import requests
import streamlit as st
import pandas as pd
from io import StringIO
from streamlit.logger import get_logger
import os

st.set_page_config(
    page_title="Gestão Equipe",
    layout="wide",
    initial_sidebar_state="expanded"
)

col1,col2,col3=st.columns([2,5,1])
with col1:
    st.image("marca-uninter-horizontal.png", use_column_width=True)
with col2:
    st.title('Gestão Equipe de Cobrança')

LOGGER = get_logger(__name__)

def atualizaBase(edited_df, baseCompleta):
    edited_df = edited_df.drop_duplicates(subset='Nome_Colaborador').reset_index(drop=True)
    base_filtrada_copy = baseCompleta.loc[baseCompleta['Nome_Colaborador'].isin(edited_df['Nome_Colaborador'])].copy()

    for i, col in enumerate(edited_df.columns):
        if i > 0:
            base_filtrada_copy[col] = base_filtrada_copy['Nome_Colaborador'].map(
                edited_df.set_index('Nome_Colaborador')[col])

    baseCompleta.update(base_filtrada_copy, overwrite=True)
    baseCompleta = baseCompleta.drop_duplicates(subset='Nome_Colaborador').reset_index(drop=True)
    
    # Salva o DataFrame como arquivo JSON localmente
    file_path = "basejson.json"
    baseCompleta.to_json(file_path, orient='records', lines=True)

    # Retorna o caminho do arquivo
    return file_path

def auto_commit(token, owner, repo, branch, file_path, content, commit_message):
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

        headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }

        response = requests.get(api_url, headers=headers)
        response_json = response.json()

        payload = {
            "message": commit_message,
            "content": content,
            "sha": response_json['sha'],
            "branch": branch
        }

        response = requests.put(api_url, headers=headers, json=payload)

        if response.status_code == 200:
            st.success("Conteúdo do arquivo atualizado com sucesso.")
        else:
            st.error(f"Erro ao atualizar conteúdo do arquivo: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Erro ao realizar commits automáticos: {e}")

def run():
    # st.write("Diretório de trabalho atual:", os.getcwd())
    
    # Leitura do arquivo JSON
    file_path = "basejson.json"
    with open(file_path, 'r') as json_file:
        # Carregar todas as linhas do JSON como uma lista
        data_lines = json_file.readlines()
    
    # Concatenar as linhas JSON na string json_data
    json_data = "[" + ",".join(data_lines) + "]"
    
    # Agora, json_data contém todos os dados JSON como uma string
    baseCompleta = pd.read_json(StringIO(json_data), orient='records')

    baseCompleta['RU']=baseCompleta['RU'].astype(str)
    baseCompleta['MATRICULA']=baseCompleta['MATRICULA'].astype(str).str.replace(".0","")
    baseCompleta=baseCompleta.loc[baseCompleta['SIT. ATUAL']!='INATIVOS']
    # baseCompleta['DATA_RETORNO']=pd.to_datetime(baseCompleta['DATA_RETORNO']).dt.strftime("%d/%m/%Y")

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
            'Selecione o Responsável',
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
        arquivo_json = atualizaBase(edited_df, baseCompleta)
        
        # Adaptar conforme a estrutura do seu arquivo e suas necessidades
        content = pd.read_json(arquivo_json, orient='records', lines=True).to_json(orient='records', lines=True)
        commit_message = "Atualização via API do GitHub."
        git_token = "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"
        auto_commit(git_token, "victorUninter", "Equipe", "main", file_path, content, commit_message)
        st.success('Atualizado com sucesso!', icon="✅")
        st.rerun()

if __name__ == "__main__":
    run()
