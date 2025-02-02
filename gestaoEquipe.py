from sqlalchemy import create_engine
import pandas as pd
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
from streamlit.logger import get_logger


class SessionState:
    def __init__(self):
        self.baseCompleta = None
        self.edited_df = None
        self.atualizar = False

# Criar uma instância da classe SessionState
session_state = SessionState()

LOGGER = get_logger(__name__)

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

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

config = {
  'host': 'roundhouse.proxy.rlwy.net',
  'user': os.getenv('MYSQLUSER'),
  'port':'26496',
  'password': os.getenv('MYSQLPASSWORD'),
  'database': 'railway'
}

# Cria a string de conexão
conn = f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

# Cria o objeto de conexão usando create_engine
engine = create_engine(conn)

def load_data():
    querySel = 'SELECT * FROM Equipe_Completa'
    return pd.read_sql(querySel, engine)

def atualizaBanco(edited_df,baseCompleta):

    baseconcat=pd.concat([edited_df,baseCompleta])
    baseconcat=baseconcat.drop_duplicates(subset='id')
    baseconcat.to_sql('Equipe_Completa', con=engine, if_exists='replace', index=False)
    engine.dispose()
    return baseconcat 

def run():
    baseCompleta = load_data()

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

    Situacao=['ATIVO','ATESTADO','FÉRIAS','FOLGA','FOLGA_ANIVERSÁRIO','AFASTADO','FALTOU','INATIVO','TREINAMENTO']
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
        DfEqpFiltro=DfEqpFiltro.query("SIT_ATUAL != 'INATIVO'")
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
                                        options=Situacao[1:],
                                        required=True,
                                    )
                                },
                                num_rows="dynamic"
                                )
        
        atualizar = st.button('ATUALIZAR',type="primary")
        # Verifica se o botão de atualização foi clicado
        # if st.button("ATUALIZAR", key="atualizar_button", type="primary"):
        #     matricula = st.text_input("Digite sua matrícula:")
        #     confirmar = st.button("Confirmar")

        #     if confirmar:
        #         matribase = len(baseCompleta[baseCompleta['MATRICULA'].str.contains(str(matricula))])

        #         if matribase >= 1:
        #             # Atualiza a variável global baseCompleta
        #             baseCompleta = atualizaBanco(edited_df, baseCompleta)
        #             st.success('Atualizado com sucesso!', icon="✅")
        #         else:
        #             st.warning("Matrícula inválida ou processo cancelado.")

    if atualizar:
        atualizaBanco(edited_df,baseCompleta)
        st.success('Atualizado com sucesso!', icon="✅")
        
if __name__ == "__main__":
    # Carregar dados no início da aplicação
    if session_state.baseCompleta is None:
        session_state.baseCompleta = load_data()

    run()

    # Atualizar o banco de dados se o botão for pressionado
    if session_state.atualizar:
        atualizaBanco(session_state.edited_df, session_state.baseCompleta)
        st.success('Atualizado com sucesso!', icon="✅")
        # Resetar o estado de atualização
        session_state.atualizar = False
