import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sqlite3
from io import BytesIO

# --- 1. CONFIGURAÇÃO VISUAL E IDENTIDADE (AZUL MARINHO) ---
st.set_page_config(page_title="OBRA PRO ERP", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #001f3f !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #001f3f !important; }
    div[data-testid="stMetricValue"] { color: #001f3f !important; font-size: 28px !important; }
    .stButton>button { background-color: #001f3f; color: white; width: 100%; border-radius: 8px; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DATOS ---
DB_FILE = "erp_obra_pro_v6.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS obras (ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome_Obra TEXT, Tipo TEXT, Valor_Contrato REAL, BDI REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS financeiro (ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Obra INTEGER, Tipo TEXT, Categoria TEXT, Valor REAL, Data TEXT, Descricao TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS equipe (ID INTEGER PRIMARY KEY AUTOINCREMENT, Nome TEXT, Cargo TEXT, Salario REAL, Obra_Alocada TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS materiais (ID INTEGER PRIMARY KEY AUTOINCREMENT, Item TEXT, Preco_Unit REAL, Qtd REAL, Obra TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS diario (ID INTEGER PRIMARY KEY AUTOINCREMENT, Data TEXT, Obra TEXT, Relato TEXT, Clima TEXT)')
    conn.commit()
    conn.close()

def g_query(sql):
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query(sql, conn)

def g_execute(sql, params):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(sql, params)
        conn.commit()

init_db()

# --- 3. SISTEMA DE LOGIN COM IMAGEM (PONTO 1 E 8) ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.markdown("""<style>.stApp { background-image: url("https://images.unsplash.com/photo-1581092160562-40aa08e78837?q=80&w=2070"); background-size: cover; }</style>""", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.write("<br><br><br>", unsafe_allow_html=True)
        st.title("🏗️ ACESSO OBRA PRO")
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        level = st.selectbox("Nível de Acesso", ["Administrador", "Engenheiro de Campo", "Financeiro"])
        if st.button("Entrar no Sistema"):
            if pw == "obras2026":
                st.session_state['auth'] = True
                st.session_state['user'] = user
                st.session_state['level'] = level
                st.rerun()
            else: st.error("Senha inválida")
else:
    # --- 4. INTERFACE PRINCIPAL ---
    st.sidebar.title(f"🛠️ {st.session_state['level']}")
    st.sidebar.write(f"Usuário: {st.session_state['user']}")
    
    menu = st.sidebar.radio("MENU GESTÃO", [
        "📊 Dashboard BI", 
        "🏗️ Gestão de Obras", 
        "💰 Financeiro", 
        "👥 Equipe (RH)", 
        "🔍 Análise de Materiais",
        "📝 Diário de Obra"
    ])

    if st.sidebar.button("Sair"):
        st.session_state['auth'] = False
        st.rerun()

    # --- ABA 1: DASHBOARD BI ---
    if menu == "📊 Dashboard BI":
        st.header("📊 Painel Geral de Gestão")
        df_f = g_query("SELECT * FROM financeiro")
        ent = df_f[df_f['Tipo'] == 'Entrada']['Valor'].sum()
        sai = df_f[df_f['Tipo'] == 'Saída']['Valor'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {ent:,.2f}")
        c2.metric("Custos Totais", f"R$ {sai:,.2f}")
        c3.metric("Lucro Líquido", f"R$ {(ent-sai):,.2f}")
        c4.metric("Margem", f"{((ent-sai)/ent*100 if ent>0 else 0):.1f}%")

        col_a, col_b = st.columns(2)
        with col_a:
            fig_sai = px.bar(df_f[df_f['Tipo'] == 'Saída'], x='Categoria', y='Valor', title="Gastos por Categoria", color_discrete_sequence=['#001f3f'])
            st.plotly_chart(fig_sai, use_container_width=True)
        with col_b:
            # Ponto 5: Impacto de Materiais
            df_m = g_query("SELECT Item, (Preco_Unit * Qtd) as Total FROM materiais")
            fig_mat = px.pie(df_m, values='Total', names='Item', title="Impacto de Custo por Material", hole=.4)
            st.plotly_chart(fig_mat, use_container_width=True)

    # --- ABA 2: GESTÃO DE OBRAS (PONTO 3) ---
    elif menu == "🏗️ Gestão de Obras":
        st.header("🏗️ Gerenciamento de Contratos")
        with st.expander("Cadastrar Nova Obra"):
            with st.form("f_obra"):
                n = st.text_input("Nome da Obra")
                t = st.selectbox("Tipo", ["Subestação", "Manutenção", "Instalação"])
                v = st.number_input("Valor Contratado")
                if st.form_submit_button("Confirmar Cadastro"):
                    g_execute("INSERT INTO obras (Nome_Obra, Tipo, Valor_Contrato) VALUES (?,?,?)", (n, t, v))
                    st.rerun()
        
        st.subheader("Obras Ativas (Edição e Exclusão)")
        df_o = g_query("SELECT * FROM obras")
        ed_o = st.data_editor(df_o, num_rows="dynamic", key="ed_o")
        if st.button("Salvar Alterações de Obras"):
            with sqlite3.connect(DB_FILE) as conn:
                ed_o.to_sql("obras", conn, if_exists="replace", index=False)
            st.success("Dados salvos!")

    # --- ABA 3: FINANCEIRO (PONTO 4) ---
    elif menu == "💰 Financeiro":
        st.header("💰 Fluxo de Caixa Detalhado")
        df_obras = g_query("SELECT * FROM obras")
        with st.expander("Novo Lançamento"):
            with st.form("f_fin"):
                o = st.selectbox("Obra", df_obras['Nome_Obra']) if not df_obras.empty else "N/A"
                tp = st.selectbox("Tipo", ["Saída", "Entrada"])
                cat = st.selectbox("Categoria", ["Mão de Obra", "Materiais", "Impostos", "Medição", "Logística"])
                val = st.number_input("Valor (R$)")
                desc = st.text_input("Observação")
                if st.form_submit_button("Lançar"):
                    g_execute("INSERT INTO financeiro (ID_Obra, Tipo, Categoria, Valor, Data, Descricao) VALUES (?,?,?,?,?,?)", 
                             (0, tp, cat, val, datetime.now().strftime("%d/%m/%Y"), desc))
                    st.rerun()
        
        df_fin = g_query("SELECT * FROM financeiro")
        st.data_editor(df_fin, num_rows="dynamic", key="ed_f")
        
        # Ponto 6: Exportação
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_fin.to_excel(writer, index=False, sheet_name='Financeiro')
        st.download_button("📥 Exportar Financeiro (Excel)", data=output.getvalue(), file_name="financeiro_obras.xlsx")

    # --- ABA 4: EQUIPE & RH (PONTO 7) ---
    elif menu == "👥 Equipe (RH)":
        st.header("👥 Gestão de Mão de Obra e Equipes")
        with st.form("f_rh"):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome do Colaborador")
            cargo = col2.text_input("Cargo/Função")
            sal = col1.number_input("Salário/Custo Mensal")
            obra_aloc = col2.selectbox("Obra Alocada", g_query("SELECT Nome_Obra FROM obras")['Nome_Obra']) if not df_obras.empty else "N/A"
            if st.form_submit_button("Cadastrar Funcionário"):
                g_execute("INSERT INTO equipe (Nome, Cargo, Salario, Obra_Alocada) VALUES (?,?,?,?)", (nome, cargo, sal, obra_aloc))
                st.rerun()
        
        st.subheader("Quadro de Funcionários")
        df_e = g_query("SELECT * FROM equipe")
        st.data_editor(df_e, num_rows="dynamic", key="ed_rh")

    # --- ABA 5: MATERIAIS (PONTO 5) ---
    elif menu == "🔍 Análise de Materiais":
        st.header("🔍 Controle de Insumos e Estoque")
        df_m = g_query("SELECT * FROM materiais")
        st.data_editor(df_m, num_rows="dynamic", key="ed_mat")
        
        if not df_m.empty:
            df_m['Total'] = df_m['Preco_Unit'] * df_m['Qtd']
            st.subheader("Análise de Impacto")
            st.write(f"Custo total em materiais: R$ {df_m['Total'].sum():,.2f}")
            fig_col = px.bar(df_m, x='Item', y='Total', title="Custo por Item", color_discrete_sequence=['#001f3f'])
            st.plotly_chart(fig_col)

    # --- ABA 6: DIÁRIO DE OBRA (PONTO 9) ---
    elif menu == "📝 Diário de Obra":
        st.header("📝 Diário de Obra Digital")
        with st.form("f_diario"):
            d_obra = st.selectbox("Obra Selecionada", g_query("SELECT Nome_Obra FROM obras")['Nome_Obra']) if not df_obras.empty else "N/A"
            d_clima = st.selectbox("Condição Climática", ["Ensolarado", "Chuva", "Nublado", "Impedimento por Clima"])
            d_relato = st.text_area("Descrição das atividades, ocorrências e visitas")
            if st.form_submit_button("Salvar Relatório Diário"):
                g_execute("INSERT INTO diario (Data, Obra, Relato, Clima) VALUES (?,?,?,?)", 
                         (datetime.now().strftime("%d/%m/%Y"), d_obra, d_relato, d_clima))
                st.success("Diário registrado com sucesso!")
        
        st.subheader("Histórico de Relatórios")
        df_d = g_query("SELECT * FROM diario")
        st.data_editor(df_d, num_rows="dynamic", key="ed_d")
