import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sqlite3

# --- 1. CONFIGURAÇÃO VISUAL (ALTA VISIBILIDADE) ---
st.set_page_config(page_title="OBRA PRO - Engenharia", layout="wide")

st.markdown("""
    <style>
    /* Fundo branco no conteúdo para leitura clara */
    .stApp { background-color: #FFFFFF; }
    
    /* Barra lateral Azul Marinho (Cor da Empresa) */
    [data-testid="stSidebar"] { background-color: #001f3f !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Títulos e Métricas em Azul Escuro */
    h1, h2, h3 { color: #001f3f !important; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="stMetricValue"] { color: #001f3f !important; font-size: 32px !important; font-weight: bold; }
    div[data-testid="stMetricLabel"] { color: #444444 !important; font-weight: bold; }
    
    /* Botões Padrão */
    .stButton>button { 
        background-color: #001f3f; 
        color: white; 
        border-radius: 8px; 
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover { background-color: #003366; border: 1px solid #ffcc00; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTÃO DO BANCO DE DATOS ---
DB_FILE = "gestao_obras_v3.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Tabela de Obras
    c.execute('''CREATE TABLE IF NOT EXISTS obras (
                    ID_Obra INTEGER PRIMARY KEY AUTOINCREMENT, 
                    Nome_Obra TEXT, 
                    Tipo_Obra TEXT, 
                    Valor_Contrato REAL, 
                    BDI_Percent REAL)''')
    # Tabela Financeira
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

# --- 3. SISTEMA DE LOGIN ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    # Tela de Login com imagem de fundo (Subestação)
    st.markdown("""
        <style>
        .stApp {
            background-image: url("https://images.unsplash.com/photo-1581092160562-40aa08e78837?q=80&w=2070");
            background-size: cover;
        }
        </style>
        """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.write("<br><br>", unsafe_allow_html=True)
        st.title("🏗️ LOGIN OBRA PRO")
        user = st.text_input("Usuário", value="admin")
        pw = st.text_input("Senha", type="password")
        if st.button("Acessar Painel"):
            if user == "admin" and pw == "obras2026":
                st.session_state['auth'] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    # --- 4. INTERFACE PRINCIPAL ---
    df_obras, df_fin = carregar_dados()
    
    st.sidebar.title("🛠️ MENU PRINCIPAL")
    menu = st.sidebar.radio("Navegação", ["📊 Painel Geral (BI)", "🏗️ Gestão de Obras", "💰 Lançamentos", "🔍 Materiais"])

    if st.sidebar.button("Sair do Sistema"):
        st.session_state['auth'] = False
        st.rerun()

    # --- ABA: DASHBOARD ---
    if menu == "📊 Painel Geral (BI)":
        st.header("📊 Resumo Financeiro da Empresa")
        
        # Cálculos de Indicadores
        total_ent = df_fin[df_fin['Tipo_Lancamento'] == 'Entrada']['Valor'].sum() if not df_fin.empty else 0
        total_sai = df_fin[df_fin['Tipo_Lancamento'] == 'Saída']['Valor'].sum() if not df_fin.empty else 0
        lucro = total_ent - total_sai
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Medições (Receita)", f"R$ {total_ent:,.2f}")
        c2.metric("Custos (Saída)", f"R$ {total_sai:,.2f}")
        c3.metric("Lucro Estimado", f"R$ {lucro:,.2f}")
        c4.metric("Obras Ativas", len(df_obras))
        
        st.divider()
        
        if not df_fin.empty:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("Custos por Categoria")
                fig_pizza = px.pie(df_fin[df_fin['Tipo_Lancamento'] == 'Saída'], values='Valor', names='Categoria', hole=0.4)
                st.plotly_chart(fig_pizza, use_container_width=True)
            with col_g2:
                st.subheader("Fluxo de Caixa")
                fig_bar = px.bar(df_fin, x='Categoria', y='Valor', color='Tipo_Lancamento', barmode='group')
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("💡 Realize lançamentos financeiros para gerar os gráficos automáticos.")

    # --- ABA: GESTÃO DE OBRAS ---
    elif menu == "🏗️ Gestão de Obras":
        st.header("🏗️ Gerenciamento de Contratos")
        
        with st.expander("➕ Adicionar Novo Contrato/Obra"):
            with st.form("form_obra"):
                nome = st.text_input("Nome da Obra/Cliente")
                tipo = st.selectbox("Tipo", ["Industrial", "Residencial", "Subestação", "Manutenção"])
                val = st.number_input("Valor Total do Contrato", min_value=0.0)
                if st.form_submit_button("Cadastrar Obra"):
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("INSERT INTO obras (Nome_Obra, Tipo_Obra, Valor_Contrato) VALUES (?,?,?)", (nome, tipo, val))
                    conn.commit()
                    st.success("Obra registrada com sucesso!")
                    st.rerun()
        
        if not df_obras.empty:
            st.subheader("Obras Cadastradas (Edição Direta)")
            st.write("Dica: Edite os valores na tabela e clique no botão abaixo para salvar.")
            
            df_edit_o = st.data_editor(df_obras, num_rows="dynamic", key="ed_obras_v3")
            
            if st.button("💾 Salvar Alterações nas Obras"):
                conn = sqlite3.connect(DB_FILE)
                df_edit_o.to_sql("obras", conn, if_exists="replace", index=False)
                st.success("Banco de dados atualizado!")
                st.rerun()

    # --- ABA: FINANCEIRO ---
    elif menu == "💰 Lançamentos":
        st.header("💰 Movimentações Financeiras")
        
        if df_obras.empty:
            st.warning("⚠️ Cadastre uma obra primeiro.")
        else:
            with st.expander("➕ Novo Lançamento"):
                with st.form("form_fin"):
                    obra_sel = st.selectbox("Obra", df_obras['Nome_Obra'])
                    tipo_l = st.selectbox("Tipo", ["Saída", "Entrada"])
                    cat_l = st.selectbox("Categoria", ["Materiais", "Mão de Obra", "Medição"])
                    valor_l = st.number_input("Valor (R$)", min_value=0.0)
                    if st.form_submit_button("Registrar"):
                        id_o = df_obras[df_obras['Nome_Obra'] == obra_sel]['ID_Obra'].iloc[0]
                        conn = sqlite3.connect(DB_FILE)
                        conn.execute("INSERT INTO financeiro (ID_Obra, Tipo_Lancamento, Categoria, Valor) VALUES (?,?,?,?)",
                                     (int(id_o), tipo_l, cat_l, valor_l))
                        conn.commit()
                        st.success("Lançamento concluído!")
                        st.rerun()

            if not df_fin.empty:
                st.subheader("Histórico (Editável)")
                df_edit_f = st.data_editor(df_fin, num_rows="dynamic", key="ed_fin_v3")
                if st.button("💾 Confirmar Ajustes Financeiros"):
                    conn = sqlite3.connect(DB_FILE)
                    df_edit_f.to_sql("financeiro", conn, if_exists="replace", index=False)
                    st.success("Histórico atualizado!")
                    st.rerun()
