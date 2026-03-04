import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sqlite3

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="OBRA PRO - Engenharia", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #001f3f !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #001f3f !important; }
    div[data-testid="stMetricValue"] { color: #001f3f !important; font-size: 32px !important; }
    .stButton>button { background-color: #001f3f; color: white; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DO BANCO DE DATOS (NOME NOVO PARA EVITAR CONFLITO) ---
DB_FILE = "database_v4_final.db" 

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS obras (
                    ID_Obra INTEGER PRIMARY KEY AUTOINCREMENT, 
                    Nome_Obra TEXT, 
                    Tipo_Obra TEXT, 
                    Valor_Contrato REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS financeiro (
                    ID_Lancamento INTEGER PRIMARY KEY AUTOINCREMENT, 
                    ID_Obra INTEGER, 
                    Data_Lancamento TEXT, 
                    Tipo_Lancamento TEXT, 
                    Categoria TEXT, 
                    Valor REAL, 
                    Descricao TEXT)''')
    conn.commit()
    conn.close()

def carregar_dados():
    conn = sqlite3.connect(DB_FILE)
    df_o = pd.read_sql_query("SELECT * FROM obras", conn)
    df_f = pd.read_sql_query("SELECT * FROM financeiro", conn)
    conn.close()
    return df_o, df_f

init_db()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.markdown("""<style>.stApp { background-image: url("https://images.unsplash.com/photo-1581092160562-40aa08e78837?q=80&w=2070"); background-size: cover; }</style>""", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.write("<br><br>", unsafe_allow_html=True)
        st.title("🏗️ LOGIN OBRA PRO")
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        if st.button("Acessar Painel"):
            if user == "admin" and pw == "obras2026":
                st.session_state['auth'] = True
                st.rerun()
            else: st.error("Incorreto.")
else:
    # --- 4. INTERFACE ---
    df_obras, df_fin = carregar_dados()
    
    st.sidebar.title("🛠️ MENU")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "🏗️ Gestão de Obras", "💰 Financeiro"])

    if menu == "📊 Dashboard":
        st.header("📊 Painel Gerencial")
        t_ent = df_fin[df_fin['Tipo_Lancamento'] == 'Entrada']['Valor'].sum() if not df_fin.empty else 0
        t_sai = df_fin[df_fin['Tipo_Lancamento'] == 'Saída']['Valor'].sum() if not df_fin.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Receitas", f"R$ {t_ent:,.2f}")
        c2.metric("Custos", f"R$ {t_sai:,.2f}")
        c3.metric("Saldo", f"R$ {(t_ent - t_sai):,.2f}")

    elif menu == "🏗️ Gestão de Obras":
        st.header("🏗️ Cadastro de Obras")
        with st.form("nova_obra"):
            n = st.text_input("Nome")
            v = st.number_input("Valor")
            if st.form_submit_button("Salvar"):
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT INTO obras (Nome_Obra, Valor_Contrato) VALUES (?,?)", (n, v))
                conn.commit()
                st.rerun()
        
        if not df_obras.empty:
            st.subheader("Obras (Editável)")
            df_edit = st.data_editor(df_obras, num_rows="dynamic")
            if st.button("Salvar Alterações"):
                conn = sqlite3.connect(DB_FILE)
                df_edit.to_sql("obras", conn, if_exists="replace", index=False)
                st.success("Salvo!")
                st.rerun()

    elif menu == "💰 Financeiro":
        st.header("💰 Lançamentos")
        if df_obras.empty: st.warning("Cadastre uma obra primeiro.")
        else:
            with st.form("fin"):
                o = st.selectbox("Obra", df_obras['Nome_Obra'])
                t = st.selectbox("Tipo", ["Saída", "Entrada"])
                v = st.number_input("Valor")
                if st.form_submit_button("Lançar"):
                    id_o = df_obras[df_obras['Nome_Obra'] == o]['ID_Obra'].iloc[0]
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("INSERT INTO financeiro (ID_Obra, Tipo_Lancamento, Valor) VALUES (?,?,?)", (int(id_o), t, v))
                    conn.commit()
                    st.rerun()
            st.data_editor(df_fin, num_rows="dynamic")
