import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sqlite3

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="OBRA PRO ERP", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #001f3f !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #001f3f !important; }
    div[data-testid="stMetricValue"] { color: #001f3f !important; font-size: 28px !important; }
    .stButton>button { background-color: #001f3f; color: white; width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DATOS INTEGRADO (TODAS AS TABELAS) ---
DB_FILE = "obra_pro_erp_v5.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Obras
    c.execute('CREATE TABLE IF NOT EXISTS obras (ID_Obra INTEGER PRIMARY KEY AUTOINCREMENT, Nome_Obra TEXT, Tipo TEXT, Valor REAL)')
    # Financeiro
    c.execute('CREATE TABLE IF NOT EXISTS financeiro (ID_Lanc INTEGER PRIMARY KEY AUTOINCREMENT, ID_Obra INTEGER, Tipo TEXT, Categoria TEXT, Valor REAL, Data TEXT)')
    # RH / Equipe
    c.execute('CREATE TABLE IF NOT EXISTS equipe (ID_Func INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT, Cargo TEXT, Salario REAL, Obra_Alocada TEXT)')
    # Materiais
    c.execute('CREATE TABLE IF NOT EXISTS materiais (ID_Mat INTEGER PRIMARY KEY AUTOINCREMENT, Nome_Item TEXT, Custo_Unit REAL, Qtd INTEGER, Impacto TEXT)')
    # Diário de Obra
    c.execute('CREATE TABLE IF NOT EXISTS diario (ID_Diario INTEGER PRIMARY KEY AUTOINCREMENT, Data TEXT, Obra TEXT, Relato TEXT, Clima TEXT)')
    conn.commit()
    conn.close()

def query(sql, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query(sql, conn, params=params)

def execute(sql, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(sql, params)
        conn.commit()

init_db()

# --- 3. LOGIN E NÍVEIS DE ACESSO ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.markdown("""<style>.stApp { background-image: url("https://images.unsplash.com/photo-1581092160562-40aa08e78837?q=80&w=2070"); background-size: cover; }</style>""", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.write("<br><br>", unsafe_allow_html=True)
        st.title("🏗️ LOGIN OBRA PRO")
        user = st.text_input("Usuário (admin ou operacional)")
        pw = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema"):
            if pw == "obras2026":
                st.session_state['auth'] = True
                st.session_state['user_type'] = user # Salva o nível de acesso
                st.rerun()
            else: st.error("Senha incorreta.")
else:
    # --- 4. INTERFACE COM TODAS AS ABAS REABILITADAS ---
    st.sidebar.title(f"👷 {st.session_state['user_type'].upper()}")
    
    # Menu com todas as funções solicitadas
    menu = st.sidebar.radio("Navegação", [
        "📊 Dashboard Geral", 
        "🏗️ Gestão de Obras", 
        "💰 Financeiro", 
        "👥 Equipe & RH", 
        "🔍 Materiais & Insumos",
        "📝 Diário de Obra"
    ])

    if st.sidebar.button("Sair"):
        st.session_state['auth'] = False
        st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard Geral":
        st.header("📊 Painel de Gestão")
        df_f = query("SELECT * FROM financeiro")
        ent = df_f[df_f['Tipo'] == 'Entrada']['Valor'].sum()
        sai = df_f[df_f['Tipo'] == 'Saída']['Valor'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento", f"R$ {ent:,.2f}")
        c2.metric("Custos Totais", f"R$ {sai:,.2f}")
        c3.metric("Margem", f"R$ {(ent-sai):,.2f}")

    # --- GESTÃO DE OBRAS ---
    elif menu == "🏗️ Gestão de Obras":
        st.header("🏗️ Cadastro e Edição de Obras")
        with st.expander("Cadastrar Nova Obra"):
            with st.form("obra"):
                n = st.text_input("Nome da Obra")
                v = st.number_input("Valor do Contrato")
                if st.form_submit_button("Salvar"):
                    execute("INSERT INTO obras (Nome_Obra, Valor) VALUES (?,?)", (n, v))
                    st.rerun()
        
        df_o = query("SELECT * FROM obras")
        st.data_editor(df_o, num_rows="dynamic", key="ed_obras")

    # --- FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.header("💰 Lançamentos de Medições e Custos")
        df_obras = query("SELECT * FROM obras")
        with st.form("fin"):
            o = st.selectbox("Obra", df_obras['Nome_Obra']) if not df_obras.empty else "Nenhuma"
            t = st.selectbox("Tipo", ["Saída", "Entrada"])
            cat = st.selectbox("Categoria", ["Mão de Obra", "Materiais", "Impostos", "Medição"])
            val = st.number_input("Valor")
            if st.form_submit_button("Lançar"):
                execute("INSERT INTO financeiro (ID_Obra, Tipo, Categoria, Valor, Data) VALUES (?,?,?,?,?)", 
                        (0, t, cat, val, datetime.now().strftime("%d/%m/%Y")))
                st.rerun()
        
        st.subheader("Histórico Editável")
        df_f = query("SELECT * FROM financeiro")
        st.data_editor(df_f, num_rows="dynamic", key="ed_fin")

    # --- EQUIPE & RH ---
    elif menu == "👥 Equipe & RH":
        st.header("👥 Gestão de Mão de Obra")
        with st.form("rh"):
            n = st.text_input("Nome do Funcionário")
            c = st.text_input("Cargo")
            s = st.number_input("Salário Mensal")
            if st.form_submit_button("Contratar"):
                execute("INSERT INTO equipe (Nome, Cargo, Salario) VALUES (?,?,?)", (n, c, s))
                st.rerun()
        
        df_e = query("SELECT * FROM equipe")
        st.data_editor(df_e, num_rows="dynamic", key="ed_rh")

    # --- MATERIAIS ---
    elif menu == "🔍 Materiais & Insumos":
        st.header("🔍 Análise de Materiais e Impacto")
        with st.form("mat"):
            item = st.text_input("Nome do Material")
            prec = st.number_input("Preço Unitário")
            qtd = st.number_input("Quantidade", step=1)
            if st.form_submit_button("Adicionar"):
                execute("INSERT INTO materiais (Nome_Item, Custo_Unit, Qtd) VALUES (?,?,?)", (item, prec, qtd))
                st.rerun()
        
        df_m = query("SELECT * FROM materiais")
        st.data_editor(df_m, num_rows="dynamic", key="ed_mat")

    # --- DIÁRIO DE OBRA ---
    elif menu == "📝 Diário de Obra":
        st.header("📝 Geração de Diário de Obra")
        col1, col2 = st.columns(2)
        with col1:
            data_d = st.date_input("Data do Relato")
            clima = st.selectbox("Clima", ["Céu Limpo", "Chuva", "Nublado"])
        with col2:
            obra_d = st.selectbox("Obra", query("SELECT Nome_Obra FROM obras")['Nome_Obra']) if not query("SELECT * FROM obras").empty else "Nenhuma"
        
        relato = st.text_area("Relato das Atividades do Dia")
        if st.button("Salvar e Gerar Diário"):
            execute("INSERT INTO diario (Data, Obra, Relato, Clima) VALUES (?,?,?,?)", 
                    (str(data_d), obra_d, relato, clima))
            st.success("Diário registrado! Use a tabela abaixo para editar ou exportar.")
        
        st.divider()
        df_d = query("SELECT * FROM diario")
        st.data_editor(df_d, num_rows="dynamic", key="ed_diario")
