import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sqlite3
import hashlib
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Gestão de Obras",
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
        st.toast("Criando banco de dados inicial...")
        # Tabela de Obras
        cursor.execute('''
            CREATE TABLE obras (
                ID_Obra INTEGER PRIMARY KEY AUTOINCREMENT, Nome_Obra TEXT NOT NULL, Tipo_Obra TEXT,
                Valor_Contrato REAL, BDI_Aplicado_Percent REAL, Data_Inicio TEXT, Data_Termino_Prevista TEXT
            )
        ''')
        # Tabela Financeira (agora com quantidade e unidade)
        cursor.execute('''
            CREATE TABLE financeiro (
                ID_Lancamento INTEGER PRIMARY KEY AUTOINCREMENT, ID_Obra INTEGER, Data_Lancamento TEXT,
                Tipo_Lancamento TEXT, Categoria TEXT, Valor REAL, Descricao TEXT,
                Quantidade REAL, Unidade TEXT,
                FOREIGN KEY (ID_Obra) REFERENCES obras (ID_Obra)
            )
        ''')
        # Dados Iniciais
        obras_iniciais = [
            ('Reforma Hospital Municipal', 'Pública', 500000, 25.0, '2026-01-15', '2026-07-31'),
            ('Manutenção Iluminação Pública', 'Pública', 200000, 28.0, '2026-02-01', '2026-05-30'),
            ('Instalação Predial Particular', 'Privada', 80000, 20.0, '2026-03-01', '2026-04-30')
        ]
        cursor.executemany("INSERT INTO obras (Nome_Obra, Tipo_Obra, Valor_Contrato, BDI_Aplicado_Percent, Data_Inicio, Data_Termino_Prevista) VALUES (?, ?, ?, ?, ?, ?)", obras_iniciais)
        financeiro_inicial = [
            (1, '2026-02-10', 'Saída', 'Materiais Elétricos', 180000, 'Cabo Flexível 2,5mm', 2000, 'm'),
            (1, '2026-02-25', 'Saída', 'Mão de Obra', 120000, 'Folha Fev/26', 1, 'cj'),
            (2, '2026-02-20', 'Saída', 'Materiais Elétricos', 95000, 'Luminária LED 150W', 50, 'pç'),
            (3, '2026-03-12', 'Saída', 'Materiais Elétricos', 12000, 'Quadro de Distribuição', 2, 'pç'),
            (1, '2026-04-05', 'Entrada', 'Medição', 250000, '1ª Medição', 1, 'cj'),
            (2, '2026-04-10', 'Entrada', 'Medição', 100000, '1ª Medição', 1, 'cj')
        ]
        cursor.executemany("INSERT INTO financeiro (ID_Obra, Data_Lancamento, Tipo_Lancamento, Categoria, Valor, Descricao, Quantidade, Unidade) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", financeiro_inicial)
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
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text
def login_user(username, password):
    users = {"admin": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"} # Senha '12345'
    return username in users and check_hashes(password, users[username])

# --- FUNÇÃO DE EXPORTAÇÃO ---
def usuário_de_login(nome_de_usuário, senha):
    if nome_de_usuário == "admin" and senha == "obras2026":
        return True
    return False
    
# --- INICIALIZAÇÃO E LÓGICA PRINCIPAL ---
init_db()

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("Sistema de Gestão de Obras Elétricas 🏗️")
    st.header("Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type='password')
    if st.button("Entrar"):
        if login_user(username, password):
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
else:
    df_obras, df_financeiro = carregar_dados()
    
    st.sidebar.title(f"Bem-vindo, Admin!")
    pagina_selecionada = st.sidebar.radio("Selecione uma página:", ["Dashboard Geral", "Dashboard por Obra", "Lançamento Financeiro", "Análise de Insumos", "Relatórios"])
    if st.sidebar.button("Sair"):
        st.session_state['authenticated'] = False
        st.rerun()

    # --- PÁGINA 1: DASHBOARD GERAL ---
    if pagina_selecionada == "Dashboard Geral":
        st.title("📊 Dashboard Geral de Obras")
        df_obras['Custo_Direto_Orcado'] = df_obras['Valor_Contrato'] / (1 + (df_obras['BDI_Aplicado_Percent'] / 100))
        gastos_por_obra = df_financeiro[df_financeiro['Tipo_Lancamento'] == 'Saída'].groupby('ID_Obra')['Valor'].sum().reset_index().rename(columns={'Valor': 'Total_Gasto'})
        df_dashboard = pd.merge(df_obras, gastos_por_obra, on='ID_Obra', how='left').fillna(0)
        df_dashboard['Percentual_Gasto'] = (df_dashboard['Total_Gasto'] / df_dashboard['Custo_Direto_Orcado']) * 100
        
        st.header("Consumo do Orçamento por Obra")
        cols = st.columns(len(df_dashboard))
        for i, row in df_dashboard.iterrows():
            with cols[i]:
                st.subheader(row['Nome_Obra'])
                fig = go.Figure(go.Indicator(mode="gauge+number", value=row['Percentual_Gasto'], title={'text': "Orçamento Consumido"}, gauge={'axis': {'range': [None, 100]}, 'steps': [{'range': [0, 70], 'color': 'lightgreen'}, {'range': [70, 90], 'color': 'yellow'}, {'range': [90, 100], 'color': 'red'}]}))
                fig.update_layout(height=250, margin={'t':30, 'b':30, 'l':30, 'r':30})
                st.plotly_chart(fig, use_container_width=True)
                st.metric(label="Gasto / Orçado (Custo Direto)", value=f"R$ {row['Total_Gasto']:,.2f}", delta=f"R$ {row['Custo_Direto_Orcado']:,.2f}", delta_color="off")

    # --- PÁGINA 2: DASHBOARD POR OBRA ---
    elif pagina_selecionada == "Dashboard por Obra":
        st.title("🏗️ Dashboard por Obra")
        obra_selecionada_nome = st.selectbox("Selecione uma Obra para Análise Detalhada", options=df_obras['Nome_Obra'])
        
        obra_detalhe = df_obras[df_obras['Nome_Obra'] == obra_selecionada_nome].iloc[0]
        financeiro_obra = df_financeiro[df_financeiro['ID_Obra'] == obra_detalhe['ID_Obra']]
        
        total_entradas = financeiro_obra[financeiro_obra['Tipo_Lancamento'] == 'Entrada']['Valor'].sum()
        total_saidas = financeiro_obra[financeiro_obra['Tipo_Lancamento'] == 'Saída']['Valor'].sum()
        saldo_contrato = obra_detalhe['Valor_Contrato'] - total_entradas
        lucro_liquido_real = total_entradas - total_saidas
        
        st.header(f"Análise da Obra: {obra_detalhe['Nome_Obra']}")
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Valor do Contrato", f"R$ {obra_detalhe['Valor_Contrato']:,.2f}")
        kpi2.metric("Saldo a Receber", f"R$ {saldo_contrato:,.2f}", help="Valor do Contrato - Total de Entradas (Medições)")
        kpi3.metric("BDI Aplicado", f"{obra_detalhe['BDI_Aplicado_Percent']}%")
        kpi4.metric("Lucro Líquido Real", f"R$ {lucro_liquido_real:,.2f}", help="Total de Entradas - Total de Saídas")
        
        st.divider()
        
        st.subheader("Materiais Comprados para esta Obra")
        materiais_obra = financeiro_obra[financeiro_obra['Categoria'] == 'Materiais Elétricos']
        if not materiais_obra.empty:
            st.dataframe(materiais_obra[['Data_Lancamento', 'Descricao', 'Quantidade', 'Unidade', 'Valor']])
        else:
            st.info("Nenhum material elétrico lançado para esta obra ainda.")

    # --- PÁGINA 3: LANÇAMENTO FINANCEIRO ---
    elif pagina_selecionada == "Lançamento Financeiro":
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
            
            submitted = st.form_submit_button("Lançar")
            if submitted:
                id_obra = df_obras[df_obras['Nome_Obra'] == obra_selecionada]['ID_Obra'].iloc[0]
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO financeiro (ID_Obra, Data_Lancamento, Tipo_Lancamento, Categoria, Valor, Descricao, Quantidade, Unidade) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (int(id_obra), data_lancamento.strftime("%Y-%m-%d"), tipo_lancamento, categoria, valor, descricao, quantidade, unidade)
                )
                conn.commit()
                conn.close()
                st.success(f"Lançamento de R$ {valor:,.2f} registrado com sucesso!")

    # --- PÁGINA 4: ANÁLISE DE INSUMOS ---
    elif pagina_selecionada == "Análise de Insumos":
        st.title("🔍 Análise de Preço Médio de Insumos")
        df_materiais = df_financeiro[(df_financeiro['Categoria'] == 'Materiais Elétricos') & (df_financeiro['Tipo_Lancamento'] == 'Saída')]
        df_materiais['Preco_Unitario'] = df_materiais['Valor'] / df_materiais['Quantidade']
        
        st.info("Esta análise usa a 'Descrição' para agrupar itens. Mantenha um padrão nas descrições para melhores resultados (ex: sempre 'Cabo Flexível 2,5mm').")
        
        itens_unicos = df_materiais['Descricao'].unique()
        item_selecionado = st.selectbox("Selecione um Insumo para Análise", options=itens_unicos)
        
        if item_selecionado:
            df_item = df_materiais[df_materiais['Descricao'] == item_selecionado]
            preco_medio = df_item['Preco_Unitario'].mean()
            unidade_item = df_item['Unidade'].iloc[0]
            
            st.metric(f"Preço Médio Pago por '{item_selecionado}'", f"R$ {preco_medio:,.2f} / {unidade_item}")
            
            st.subheader("Histórico de Compras deste Item")
            st.dataframe(df_item[['Data_Lancamento', 'Quantidade', 'Unidade', 'Preco_Unitario', 'Valor']])

    # --- PÁGINA 5: RELATÓRIOS ---
    elif pagina_selecionada == "Relatórios":
        st.title("📄 Gerador de Relatórios")
        st.subheader("Relatório de Medição para Obras Públicas")
        
        obras_publicas = df_obras[df_obras['Tipo_Obra'] == 'Pública']['Nome_Obra']
        obra_relatorio_nome = st.selectbox("Selecione a Obra Pública", obras_publicas)
        
        if obra_relatorio_nome:
            obra_info = df_obras[df_obras['Nome_Obra'] == obra_relatorio_nome].iloc[0]
            financeiro_obra = df_financeiro[df_financeiro['ID_Obra'] == obra_info['ID_Obra']]
            total_entradas = financeiro_obra[financeiro_obra['Tipo_Lancamento'] == 'Entrada']['Valor'].sum()
            total_saidas = financeiro_obra[financeiro_obra['Tipo_Lancamento'] == 'Saída']['Valor'].sum()
            
            dados_relatorio = {
                'Descrição': ['Valor Total do Contrato', 'Total de Medições Aprovadas', 'Saldo a Medir', 'Total de Custos Realizados'],
                'Valor': [obra_info['Valor_Contrato'], total_entradas, obra_info['Valor_Contrato'] - total_entradas, total_saidas]
            }
            df_relatorio = pd.DataFrame(dados_relatorio)
            
            st.table(df_relatorio.style.format({'Valor': 'R$ {:,.2f}'}))
            
            st.download_button(
                label="📥 Exportar Relatório para Excel",
                data=to_excel(df_relatorio),
                file_name=f"Relatorio_Medicao_{obra_relatorio_nome.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
