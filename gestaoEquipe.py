from sqlalchemy import create_engine
import pandas as pd
import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="Gestão Equipe",
    layout="wide",
    initial_sidebar_state="expanded"
)

# banco de dados

col1,col2=st.columns([3,10])
with col1:
    st.image('marca-uninter-horizontal.png')
with col2:
    st.title('GESTÃO EQUIPE DE COBRANÇA')

config = {
  'host': 'roundhouse.proxy.rlwy.net',
  'user': 'root',
  'port':'26496',
  'password': '2b632BA2FhGFeFb4BHdcdC3G6B6-6-3d',
  'database': 'railway'
}

# Cria a string de conexão
conn = f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

# Cria o objeto de conexão usando create_engine
engine = create_engine(conn)

def atualizaBanco(edited_df,baseCompleta):

    baseconcat=pd.concat([edited_df,baseCompleta])
    baseconcat=baseconcat.drop_duplicates(subset='id')
    baseconcat.to_sql('Equipe_Completa', con=engine, if_exists='replace', index=False)
    engine.dispose()
    return 

def run():
    
    querySel='SELECT * FROM Equipe_Completa'
    baseCompleta=pd.read_sql(querySel,engine)

    # Convertendo colunas para os tipos desejados
    baseCompleta['RU'] = baseCompleta['RU'].astype(str)
    baseCompleta['MATRICULA'] = baseCompleta['MATRICULA'].astype(str).str.replace(".0", "")

    # Filtrando linhas com 'SIT. ATUAL' diferente de 'INATIVOS'
    baseCompleta = baseCompleta.loc[baseCompleta['SIT_ATUAL'] != 'INATIVOS'].reset_index(drop=True)

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
        atualizaBanco(edited_df,baseCompleta)
        st.success('Atualizado com sucesso!', icon="✅")
        st.rerun()
        

if __name__ == "__main__":
    run()
