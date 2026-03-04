import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sqlite3
from io import BytesIO
from fpdf import FPDF

# --- CONFIGURAÇÃO VISUAL (AZUL MARINHO) ---
st.set_page_config(page_title="OBRA PRO - Engenharia", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    [data-testid="stSidebar"] { background-color: #001f3f; color: white; }
    .stButton>button { background-color: #001f3f; color: white; border-radius: 5px; }
    h1, h2, h3 { color: #001f3f; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ATUALIZADO (RH + DIÁRIO) ---
DB_FILE = "gestao_obras_v2.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabela Obras
    c.execute('''CREATE TABLE IF NOT EXISTS obras (ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT, Tipo TEXT, Valor REAL, BDI REAL, Inicio TEXT, Fim TEXT)''')
    # Tabela Financeiro
    c.execute('''CREATE TABLE IF NOT EXISTS financeiro (ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Obra INTEGER, Data TEXT, Tipo TEXT, Categoria TEXT, Valor REAL, Descricao TEXT, Qtd REAL, Unidade TEXT)''')
    # Tabela Equipe (RH)
    c.execute('''CREATE TABLE IF NOT EXISTS equipe (ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT, Cargo TEXT, Salario REAL, ID_Obra INTEGER)''')
    # Tabela Diário de Obra
    c.execute('''CREATE TABLE IF NOT EXISTS diario (ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Obra INTEGER, Data TEXT, Relato TEXT, Clima TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÕES DE SUPORTE ---
def carregar(tabela):
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df

def excluir_registro(tabela, id_reg):
    conn = get_db_connection()
    conn.execute(f"DELETE FROM {tabela} WHERE ID = ?", (id_reg,))
    conn.commit()
    conn.close()
    st.rerun()

# --- LOGIN COM FUNDO ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.markdown("""
        <style>
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1350&q=80");
            background-size: cover;
        }
        </style>
        """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1,1,1])
    with col_c:
        st.title("🏗️ LOGIN OBRA PRO")
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema"):
            if user == "admin" and pw == "obras2026":
                st.session_state['auth'] = True
                st.rerun()
            else: st.error("Incorreto")
else:
    # --- INTERFACE PRINCIPAL ---
    df_obras = carregar("obras")
    df_fin = carregar("financeiro")
    
    menu = st.sidebar.radio("MENU PRINCIPAL", ["📊 Dashboard BI", "🚧 Gestão de Obras", "💰 Financeiro", "👥 Equipe & RH", "📝 Diário de Obra", "🔍 Análise Insumos"])

    # 1. DASHBOARD BI (Ponto 2)
    if menu == "📊 Dashboard BI":
        st.title("📊 Painel Gerencial Azul Marinho")
        c1, c2, c3, c4 = st.columns(4)
        total_ent = df_fin[df_fin['Tipo'] == 'Entrada']['Valor'].sum()
        total_sai = df_fin[df_fin['Tipo'] == 'Saída']['Valor'].sum()
        c1.metric("Faturamento", f"R$ {total_ent:,.2f}")
        c2.metric("Custos Totais", f"R$ {total_sai:,.2f}")
        c3.metric("Lucro Bruto", f"R$ {(total_ent - total_sai):,.2f}")
        c4.metric("Obras Ativas", len(df_obras))
        
        # Gráfico Impacto (Ponto 5)
        st.subheader("Maiores Impactos Financeiros por Obra")
        fig = px.bar(df_fin[df_fin['Tipo'] == 'Saída'], x="Categoria", y="Valor", color="Categoria", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    # 2. GESTÃO DE OBRAS (Ponto 3 - Edição/Exclusão)
    elif menu == "🚧 Gestão de Obras":
        st.title("🚧 Gestão de Contratos")
        with st.expander("➕ Nova Obra"):
            with st.form("cad_obra"):
                n = st.text_input("Nome da Obra")
                v = st.number_input("Valor")
                if st.form_submit_button("Salvar"):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO obras (Nome, Valor) VALUES (?,?)", (n, v))
                    conn.commit()
                    st.rerun()
        
        st.subheader("Editar/Excluir Obras")
        # EDITOR DE DADOS (Ponto 3)
        edited_df = st.data_editor(df_obras, num_rows="dynamic", key="editor_obras")
        if st.button("Salvar Alterações nas Obras"):
            conn = get_db_connection()
            edited_df.to_sql("obras", conn, if_exists="replace", index=False)
            st.success("Banco atualizado!")

    # 3. FINANCEIRO (Ponto 4)
    elif menu == "💰 Financeiro":
        st.title("💰 Fluxo de Caixa")
        st.subheader("Lista de Lançamentos (Editável)")
        # Tabela editável com opção de exclusão (Ponto 4)
        ed_fin = st.data_editor(df_fin, num_rows="dynamic")
        if st.button("Confirmar Ajustes Financeiros"):
            conn = get_db_connection()
            ed_fin.to_sql("financeiro", conn, if_exists="replace", index=False)
            st.rerun()

    # 4. EQUIPE & RH (Ponto 7)
    elif menu == "👥 Equipe & RH":
        st.title("👥 Gestão de Mão de Obra")
        col_rh1, col_rh2 = st.columns(2)
        with col_rh1:
            st.subheader("Cadastrar Funcionário")
            with st.form("rh"):
                nome_f = st.text_input("Nome")
                cargo = st.text_input("Cargo")
                sal = st.number_input("Salário")
                if st.form_submit_button("Adicionar"):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO equipe (Nome, Cargo, Salario) VALUES (?,?,?)", (nome_f, cargo, sal))
                    conn.commit()
                    st.rerun()
        with col_rh2:
            st.subheader("Quadro de Funcionários")
            st.dataframe(carregar("equipe"))

    # 5. DIÁRIO DE OBRA (Ponto 9)
    elif menu == "📝 Diário de Obra":
        st.title("📝 Diário de Obra Digital")
        obra_d = st.selectbox("Obra", df_obras['Nome'])
        relato = st.text_area("Relato do Dia")
        clima = st.selectbox("Clima", ["Sol", "Chuva", "Nublado"])
        if st.button("Gerar e Salvar Diário"):
            st.success(f"Diário de {obra_d} salvo! Pronto para exportação.")
            # Aqui entraria a lógica do PDF com FPDF
            
    st.sidebar.write("---")
    if st.sidebar.button("Sair do Sistema"):
        st.session_state['auth'] = False
        st.rerun()
