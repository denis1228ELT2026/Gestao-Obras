import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sqlite3
from io import BytesIO
from fpdf import FPDF

# --- CONFIGURAÇÃO VISUAL REFINADA (ALTA VISIBILIDADE) ---
st.set_page_config(page_title="OBRA PRO - Engenharia", layout="wide")

st.markdown("""
    <style>
    /* Fundo geral mais claro para leitura e Sidebar Azul Marinho */
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #001f3f; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Estilo dos Cards de indicadores no Painel */
    div[data-testid="stMetricValue"] { color: #001f3f !important; font-weight: bold; }
    div[data-testid="stMetricLabel"] { color: #555555 !important; }
    
    /* Botões padrão da empresa */
    .stButton>button { 
        background-color: #001f3f; 
        color: white; 
        border-radius: 8px; 
        width: 100%;
        border: none;
    }
    .stButton>button:hover { background-color: #003366; color: #ffcc00; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM O BANCO DE DATOS ---
DB_FILE = "gestao_obras.db" # Usando o seu nome de arquivo original

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def carregar_dados():
    conn = get_db_connection()
    df_obras = pd.read_sql_query("SELECT * FROM obras", conn)
    df_financeiro = pd.read_sql_query("SELECT * FROM financeiro", conn)
    conn.close()
    df_obras['Data_Inicio'] = pd.to_datetime(df_obras['Data_Inicio'])
    df_financeiro['Data_Lancamento'] = pd.to_datetime(df_financeiro['Data_Lancamento'])
    return df_obras, df_financeiro

# --- LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    # Imagem de fundo na tela de login
    st.markdown("""
        <style>
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1581092160562-40aa08e78837?q=80&w=2070");
            background-size: cover;
        }
        </style>
        """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1,1.5,1])
    with col_c:
        st.write("<br><br><br>", unsafe_allow_html=True)
        st.title("🏗️ LOGIN OBRA PRO")
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        if st.button("Entrar no Sistema"):
            if user == "admin" and pw == "obras2026":
                st.session_state['authenticated'] = True
                st.rerun()
            else: st.error("Usuário ou senha incorretos")
else:
    # --- INTERFACE PRINCIPAL APÓS LOGIN ---
    df_obras, df_financeiro = carregar_dados()
    
    st.sidebar.title("🏗️ MENU PRINCIPAL")
    menu = st.sidebar.radio("Navegação", [
        "📊 Dashboard Geral (BI)", 
        "🏗️ Gestão de Obras", 
        "💰 Lançamento Financeiro", 
        "👥 Equipe & RH",
        "📝 Diário de Obra",
        "🔍 Análise de Materiais"
    ])

    if st.sidebar.button("Sair"):
        st.session_state['authenticated'] = False
        st.rerun()

    # 1. DASHBOARD GERAL (ESTILO OBRA PRIMA COM CORES CORRIGIDAS)
    if menu == "📊 Dashboard Geral (BI)":
        st.title("📊 Painel Gerencial Financeiro")
        
        # Cálculos rápidos
        total_entradas = df_financeiro[df_financeiro['Tipo_Lancamento'] == 'Entrada']['Valor'].sum()
        total_saidas = df_financeiro[df_financeiro['Tipo_Lancamento'] == 'Saída']['Valor'].sum()
        lucro = total_entradas - total_saidas
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Medições (Entrada)", f"R$ {total_entradas:,.2f}")
        c2.metric("Total Custos (Saída)", f"R$ {total_saidas:,.2f}")
        c3.metric("Lucro Bruto Atual", f"R$ {lucro:,.2f}")
        c4.metric("Obras em Andamento", len(df_obras))

        st.divider()
        
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Entradas vs Saídas por Mês")
            # Gráfico de barras agrupadas
            fig_bar = px.bar(df_financeiro, x=df_financeiro['Data_Lancamento'].dt.strftime('%b/%y'), y='Valor', 
                             color='Tipo_Lancamento', barmode='group',
                             color_discrete_map={'Entrada': '#2ecc71', 'Saída': '#e74c3c'})
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_graf2:
            st.subheader("Distribuição de Custos")
            fig_pie = px.pie(df_financeiro[df_financeiro['Tipo_Lancamento'] == 'Saída'], values='Valor', names='Categoria', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    # 2. GESTÃO DE OBRAS (COM EDIÇÃO E EXCLUSÃO)
    elif menu == "🏗️ Gestão de Obras":
        st.title("🏗️ Gestão de Obras e Contratos")
        
        tab1, tab2 = st.tabs(["Lista de Obras (Editar/Excluir)", "Cadastrar Nova Obra"])
        
        with tab1:
            st.write("Dica: Altere os dados diretamente na tabela e clique em Salvar.")
            # Editor de dados do Streamlit (Ponto 3 do seu pedido)
            df_edit_obras = st.data_editor(df_obras, num_rows="dynamic", key="editor_obras_v3")
            if st.button("Salvar Alterações nas Obras"):
                conn = get_db_connection()
                df_edit_obras.to_sql("obras", conn, if_exists="replace", index=False)
                st.success("Dados das obras atualizados com sucesso!")
        
        with tab2:
            with st.form("form_nova_obra"):
                n = st.text_input("Nome da Obra")
                t = st.selectbox("Tipo", ["Pública", "Privada"])
                v = st.number_input("Valor do Contrato", min_value=0.0)
                b = st.number_input("BDI (%)", value=25.0)
                if st.form_submit_button("Cadastrar Obra"):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO obras (Nome_Obra, Tipo_Obra, Valor_Contrato, BDI_Aplicado_Percent) VALUES (?,?,?,?)", (n,t,v,b))
                    conn.commit()
                    st.success("Obra cadastrada!")
                    st.rerun()

    # 3. FINANCEIRO (SEU CÓDIGO ORIGINAL VOLTANDO A FUNCIONAR)
    elif menu == "💰 Lançamento Financeiro":
        st.title("💰 Lançamentos Financeiros")
        
        # Área de Lançamento
        with st.expander("➕ Realizar Novo Lançamento"):
            with st.form("novo_fin"):
                obra_sel = st.selectbox("Obra", df_obras['Nome_Obra'])
                tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
                cat = st.selectbox("Categoria", ["Materiais Elétricos", "Mão de Obra", "Impostos", "Medição", "Outros"])
                val = st.number_input("Valor", min_value=0.0)
                desc = st.text_input("Descrição")
                if st.form_submit_button("Lançar"):
                    id_o = df_obras[df_obras['Nome_Obra'] == obra_sel]['ID_Obra'].iloc[0]
                    conn = get_db_connection()
                    conn.execute("INSERT INTO financeiro (ID_Obra, Tipo_Lancamento, Categoria, Valor, Descricao, Data_Lancamento) VALUES (?,?,?,?,?,?)",
                                 (int(id_o), tipo, cat, val, desc, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Lançado!")
                    st.rerun()

        st.subheader("Histórico Completo (Editável)")
        df_edit_fin = st.data_editor(df_financeiro, num_rows="dynamic", key="editor_fin_v3")
        if st.button("Salvar Alterações Financeiras"):
            conn = get_db_connection()
            df_edit_fin.to_sql("financeiro", conn, if_exists="replace", index=False)
            st.success("Financeiro atualizado!")
            st.rerun()

    # (Outras abas como Equipe e Diário de Obra seguem o mesmo padrão...)
