import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sqlite3
import hashlib
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="OBRA PRO - Gestão Elétrica",
    page_icon="🏗️",
    layout="wide"
)

# --- BANCO DE DADOS SQLITE ---
DB_FILE = "gestao_obras.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='obras'")
    if cursor.fetchone() is None:
        # Tabela de Obras
        cursor.execute('''
            CREATE TABLE obras (
                ID_Obra INTEGER PRIMARY KEY AUTOINCREMENT, Nome_Obra TEXT NOT NULL, Tipo_Obra TEXT,
                Valor_Contrato REAL, BDI_Aplicado_Percent REAL, Data_Inicio TEXT, Data_Termino_Prevista TEXT
            )
        ''')
        # Tabela Financeira
        cursor.execute('''
            CREATE TABLE financeiro (
                ID_Lancamento INTEGER PRIMARY KEY AUTOINCREMENT, ID_Obra INTEGER, Data_Lancamento TEXT,
                Tipo_Lancamento TEXT, Categoria TEXT, Valor REAL, Descricao TEXT,
                Quantidade REAL, Unidade TEXT,
                FOREIGN KEY (ID_Obra) REFERENCES obras (ID_Obra)
            )
        ''')
        conn.commit()
    conn.close()

def carregar_dados():
    conn = get_db_connection()
    df_obras = pd.read_sql_query("SELECT * FROM obras", conn)
    df_financeiro = pd.read_sql_query("SELECT * FROM financeiro", conn)
    conn.close()
    df_obras['Data_Inicio'] = pd.to_datetime(df_obras['Data_Inicio'])
    df_obras['Data_Termino_Prevista'] = pd.to_datetime(df_obras['Data_Termino_Prevista'])
    df_financeiro['Data_Lancamento'] = pd.to_datetime(df_financeiro['Data_Lancamento'])
    return df_obras, df_financeiro

# --- FUNÇÕES DE LOGIN ---
def login_user(username, password):
    users = {"admin": "obras2026"} 
    if username in users and users[username] == password:
        return True
    return False

# --- FUNÇÃO DE EXPORTAÇÃO ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    processed_data = output.getvalue()
    return processed_data

# --- INICIALIZAÇÃO ---
init_db()

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# --- TELA DE LOGIN ---
if not st.session_state['authenticated']:
    st.title("Sistema de Gestão de Obras Elétricas 🏗️")
    st.header("Conecte-se")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type='password')
    if st.button("Entrar"):
        if login_user(username, password):
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# --- SISTEMA PÓS-LOGIN ---
else:
    df_obras, df_financeiro = carregar_dados()
    
    # MENU LATERAL ESTILO "OBRA PRIMA"
    st.sidebar.title("🏗️ OBRA PRO v1.0")
    st.sidebar.markdown(f"**Usuário:** Admin")
    
    pagina = st.sidebar.radio("Navegação", [
        "Painel Gerencial", 
        "Gestão de Obras", 
        "Lançamento Financeiro", 
        "Análise de Insumos", 
        "Relatórios",
        "Configurações"
    ])
    
    if st.sidebar.button("Sair"):
        st.session_state['authenticated'] = False
        st.rerun()

    # --- ABA 1: PAINEL GERENCIAL (ESTILO OBRA PRIMA) ---
    if pagina == "Painel Gerencial":
        st.title("📊 Painel Gerencial - BI")
        
        # Cálculos para os Cards
        total_contratos = df_obras['Valor_Contrato'].sum()
        total_recebido = df_financeiro[df_financeiro['Tipo_Lancamento'] == 'Entrada']['Valor'].sum()
        total_pago = df_financeiro[df_financeiro['Tipo_Lancamento'] == 'Saída']['Valor'].sum()
        
        # Linha de Indicadores (Cards)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total em Contratos", f"R$ {total_contratos:,.2f}")
        c2.metric("Total Recebido (Medições)", f"R$ {total_recebido:,.2f}", delta="Entradas")
        c3.metric("Total Pago (Custos)", f"R$ {total_pago:,.2f}", delta="-Saídas", delta_color="inverse")
        c4.metric("Saldo em Caixa", f"R$ {(total_recebido - total_pago):,.2f}")

        st.divider()

        # Gráficos de Fluxo (Simulando a imagem do Obra Prima)
        col_esq, col_dir = st.columns(2)
        
        with col_esq:
            st.subheader("Fluxo de Caixa Mensal")
            fluxo_mensal = df_financeiro.groupby([df_financeiro['Data_Lancamento'].dt.strftime('%b'), 'Tipo_Lancamento'])['Valor'].sum().unstack().fillna(0)
            if not fluxo_mensal.empty:
                fig_fluxo = px.bar(fluxo_mensal, barmode='group', color_discrete_map={'Entrada': '#2ecc71', 'Saída': '#e74c3c'})
                st.plotly_chart(fig_fluxo, use_container_width=True)
            else:
                st.info("Aguardando lançamentos para gerar gráfico.")

        with col_dir:
            st.subheader("Distribuição de Custos por Obra")
            custos_obra = df_financeiro[df_financeiro['Tipo_Lancamento'] == 'Saída'].merge(df_obras, on='ID_Obra')
            if not custos_obra.empty:
                fig_pizza = px.pie(custos_obra, values='Valor', names='Nome_Obra', hole=0.4)
                st.plotly_chart(fig_pizza, use_container_width=True)
            else:
                st.info("Sem dados de custos.")

    # --- ABA 2: GESTÃO DE OBRAS (INTEGRADA COM SEU CÓDIGO) ---
    elif pagina == "Gestão de Obras":
        st.title("📂 Gestão e Cadastro de Obras")
        
        aba_obra = st.tabs(["Dashboard por Obra", "Cadastrar Nova Obra", "Lista de Obras"])
        
        with aba_obra[0]:
            # SEU CÓDIGO ORIGINAL DE ANÁLISE POR OBRA
            obra_selecionada_nome = st.selectbox("Selecione uma Obra", options=df_obras['Nome_Obra'])
            obra_detalhe = df_obras[df_obras['Nome_Obra'] == obra_selecionada_nome].iloc[0]
            fin_obra = df_financeiro[df_financeiro['ID_Obra'] == obra_detalhe['ID_Obra']]
            
            ent = fin_obra[fin_obra['Tipo_Lancamento'] == 'Entrada']['Valor'].sum()
            sai = fin_obra[fin_obra['Tipo_Lancamento'] == 'Saída']['Valor'].sum()
            
            st.subheader(f"Status: {obra_detalhe['Nome_Obra']}")
            k1, k2, k3 = st.columns(3)
            k1.metric("Contrato", f"R$ {obra_detalhe['Valor_Contrato']:,.2f}")
            k2.metric("Gasto Real", f"R$ {sai:,.2f}")
            k3.metric("Lucro Atual", f"R$ {(ent - sai):,.2f}")
            
            # Gráfico de Gauge que você tinha
            progresso = (sai / (obra_detalhe['Valor_Contrato'] / (1 + obra_detalhe['BDI_Aplicado_Percent']/100))) * 100
            fig_g = go.Figure(go.Indicator(mode="gauge+number", value=progresso, title={'text': "% Orçamento Consumido"}, gauge={'axis': {'range': [None, 100]}}))
            fig_g.update_layout(height=300)
            st.plotly_chart(fig_g)

        with aba_obra[1]:
            # NOVO FORMULÁRIO DE CADASTRO
            st.subheader("Adicionar Novo Contrato Elétrico")
            with st.form("nova_obra"):
                nome = st.text_input("Nome da Obra")
                tipo = st.selectbox("Tipo", ["Pública", "Privada"])
                valor = st.number_input("Valor Total do Contrato", min_value=0.0)
                bdi = st.number_input("BDI Aplicado (%)", min_value=0.0, value=25.0)
                d_ini = st.date_input("Data de Início")
                d_fim = st.date_input("Previsão de Término")
                if st.form_submit_button("Salvar Obra"):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO obras (Nome_Obra, Tipo_Obra, Valor_Contrato, BDI_Aplicado_Percent, Data_Inicio, Data_Termino_Prevista) VALUES (?, ?, ?, ?, ?, ?)",
                                 (nome, tipo, valor, bdi, d_ini.strftime("%Y-%m-%d"), d_fim.strftime("%Y-%m-%d")))
                    conn.commit()
                    conn.close()
                    st.success("Obra cadastrada!")
                    st.rerun()

        with aba_obra[2]:
            st.dataframe(df_obras)

    # --- ABA 3: LANÇAMENTO FINANCEIRO (SEU CÓDIGO ORIGINAL) ---
    elif pagina == "Lançamento Financeiro":
        st.title("📝 Lançamento Financeiro")
        with st.form("lancamento_form", clear_on_submit=True):
            obra_selecionada = st.selectbox("Selecione a Obra", options=df_obras['Nome_Obra'])
            tipo_lancamento = st.selectbox("Tipo de Lançamento", ["Saída", "Entrada"])
            data_lancamento = st.date_input("Data do Lançamento", value=datetime.now())
            categoria = st.selectbox("Categoria", options=['Materiais Elétricos', 'Mão de Obra', 'Impostos', 'Medição', 'Custo Fixo', 'Outros'])
            valor = st.number_input("Valor Total (R$)", min_value=0.01, format="%.2f")
            descricao = st.text_input("Descrição (Ex: NF-e 1234, Fornecedor XYZ, Cabo 2,5mm)")
            
            col_qtd, col_un = st.columns(2)
            with col_qtd:
                quantidade = st.number_input("Quantidade", min_value=0.0, format="%.2f", value=1.0)
            with col_un:
                unidade = st.selectbox("Unidade", ["un", "pç", "m", "kg", "cj", "vb"])
            
            submitted = st.form_submit_button("Registrar Lançamento")
            if submitted:
                id_obra = df_obras[df_obras['Nome_Obra'] == obra_selecionada]['ID_Obra'].iloc[0]
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO financeiro (ID_Obra, Data_Lancamento, Tipo_Lancamento, Categoria, Valor, Descricao, Quantidade, Unidade) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (int(id_obra), data_lancamento.strftime("%Y-%m-%d"), tipo_lancamento, categoria, valor, descricao, quantidade, unidade)
                )
                conn.commit()
                conn.close()
                st.success(f"Lançamento de R$ {valor:,.2f} registrado!")

    # --- ABA 4: ANÁLISE DE INSUMOS (SEU CÓDIGO ORIGINAL) ---
    elif pagina == "Análise de Insumos":
        st.title("🔍 Inteligência de Materiais")
        df_materiais = df_financeiro[(df_financeiro['Categoria'] == 'Materiais Elétricos') & (df_financeiro['Tipo_Lancamento'] == 'Saída')]
        if not df_materiais.empty:
            df_materiais['Preco_Unitario'] = df_materiais['Valor'] / df_materiais['Quantidade']
            item_selecionado = st.selectbox("Selecione um Insumo", options=df_materiais['Descricao'].unique())
            df_item = df_materiais[df_materiais['Descricao'] == item_selecionado]
            st.metric(f"Preço Médio: {item_selecionado}", f"R$ {df_item['Preco_Unitario'].mean():,.2f}")
            st.dataframe(df_item)
        else:
            st.warning("Sem dados de materiais para analisar.")

    # --- ABA 5: RELATÓRIOS (SEU CÓDIGO ORIGINAL) ---
    elif pagina == "Relatórios":
        st.title("📄 Relatórios e Exportação")
        obra_rel = st.selectbox("Filtrar por Obra Pública", df_obras[df_obras['Tipo_Obra'] == 'Pública']['Nome_Obra'])
        if obra_rel:
            id_rel = df_obras[df_obras['Nome_Obra'] == obra_rel]['ID_Obra'].iloc[0]
            df_final = df_financeiro[df_financeiro['ID_Obra'] == id_rel]
            st.dataframe(df_final)
            st.download_button("Exportar para Excel", data=to_excel(df_final), file_name="Relatorio_Obra.xlsx")
