import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import date
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Logística XYZ - FleetTrace",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CSS 
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
/* Tema Claro/Creme Suave */
.stApp { background: linear-gradient(135deg, #fdfbf7 0%, #f4f1ea 100%); color: #1f2937; }
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid rgba(0,0,0,0.05);
}
/* Ocultar scrollbar da sidebar e forçar altura */
[data-testid="stSidebarNav"] { display: none; }
section[data-testid="stSidebar"] > div {
    height: 100vh;
    overflow-y: hidden !important;
}

.metric-card {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 16px; padding: 24px; text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    transition: all 0.3s ease;
}
.metric-card:hover {
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}
.metric-card .icon { font-size: 2.2rem; margin-bottom: 8px; }
.metric-card .value { font-size: 2rem; font-weight: 800; color: #2563eb; line-height: 1; }
.metric-card .label { color: #6b7280; font-size: 0.8rem; margin-top: 6px; text-transform: uppercase; letter-spacing: 1px; }

.login-container {
    background: #ffffff;
    border: 1px solid rgba(0,0,0,0.05); border-radius: 24px; padding: 48px 40px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}
.section-header {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 24px; padding-bottom: 16px;
    border-bottom: 1px solid rgba(0,0,0,0.05);
}
.section-header h2 { margin: 0; font-size: 1.8rem; font-weight: 700; color: #1f2937; }
.section-header span { color: #6b7280; font-size: 0.9rem; font-weight: 500; }

.user-badge {
    background: rgba(37, 99, 235, 0.05);
    border: 1px solid rgba(37, 99, 235, 0.1);
    border-radius: 12px; padding: 12px;
    display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
}
.stButton>button {
    border-radius: 8px !important; font-weight: 600 !important;
    padding: 0.5rem 1rem !important; transition: all 0.2s;
}
.stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input {
    border-radius: 8px !important; background: #ffffff !important;
    border: 1px solid rgba(0,0,0,0.1) !important; color: #1f2937 !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# COMPONENTES UI
# ==========================================
def render_metric_card(icon, value, label):
    st.markdown(f"""
    <div class="metric-card">
        <div class="icon">{icon}</div>
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def section_header(icon, title, subtitle):
    st.markdown(f"""
    <div class="section-header">
        <div style="font-size:2rem">{icon}</div>
        <div><h2>{title}</h2><span>{subtitle}</span></div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# BANCO DE DADOS
# ==========================================
DB_NAME = "fleettrace.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'operator',
        display_name TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS veiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT UNIQUE NOT NULL,
        modelo TEXT NOT NULL,
        ano INTEGER,
        intervalo_km INTEGER NOT NULL DEFAULT 10000,
        intervalo_meses INTEGER NOT NULL DEFAULT 6,
        ativo BOOLEAN NOT NULL DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS manutencoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT NOT NULL,
        data_servico DATE NOT NULL,
        km_atual INTEGER,
        oficina TEXT NOT NULL,
        tipo_servico TEXT NOT NULL,
        descricao TEXT,
        custo REAL NOT NULL,
        aceite_lgpd BOOLEAN NOT NULL DEFAULT 1,
        criado_por TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (placa) REFERENCES veiculos(placa)
    )""")
    
    c.execute("SELECT * FROM users WHERE username=?", ("carlos.silva",))
    if not c.fetchone():
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role, display_name) VALUES (?,?,?,?)",
                  ("carlos.silva", hashed_pw, "admin", "Carlos Silva"))
    conn.commit()
    conn.close()
    populate_sample_data()

def populate_sample_data():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM veiculos")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    veiculos = [
        ("ABC-1234", "Toyota Hilux",     2021, 10000, 6, 1),
        ("DEF-5678", "Volkswagen Amarok", 2022, 10000, 6, 1),
        ("GHI-9012", "Ford Ranger",       2020, 10000, 6, 1),
        ("JKL-3456", "Chevrolet S10",     2019, 10000, 6, 1),
        ("MNO-7890", "Fiat Toro",         2023, 10000, 12, 1),
        ("PQR-2345", "Renault Duster",    2021, 15000, 12, 1),
        ("STU-6789", "Jeep Renegade",     2022, 15000, 12, 1),
        ("VWX-0123", "Honda HR-V",        2020, 10000, 12, 1),
    ]
    c.executemany("INSERT INTO veiculos (placa, modelo, ano, intervalo_km, intervalo_meses, ativo) VALUES (?,?,?,?,?,?)", veiculos)

    registros = [
        ("ABC-1234", "2024-03-10", 62000, "Oficina Gilbert Auto",     "Troca de Oleo",    "Troca de oleo 5W30",              320.0, True, "carlos.silva"),
        ("ABC-1234", "2024-07-22", 75000, "Oficina Gilbert Auto",     "Revisao Geral",    "Revisao dos 75 mil km",           1850.0, True, "carlos.silva"),
        ("ABC-1234", "2025-01-15", 87000, "Centro Automotivo Norte",  "Freios",           "Pastilhas e discos",              980.0, True, "carlos.silva"),
        ("DEF-5678", "2024-05-03", 45000, "Oficina Gilbert Auto",     "Troca de Oleo",    "Oleo diesel 5W40",                410.0, True, "carlos.silva"),
        ("DEF-5678", "2024-11-18", 60000, "VW Concessionaria GO",     "Revisao Geral",    "Revisao completa",               2350.0, True, "carlos.silva"),
        ("DEF-5678", "2025-04-02", 63000, "Oficina Gilbert Auto",     "Suspensao",        "Amortecedor",                    1200.0, True, "carlos.silva"),
        ("GHI-9012", "2023-08-14", 89000, "Ford Autorizada Goiania",  "Revisao Geral",    "Revisao 90 mil km",              2100.0, True, "carlos.silva"),
        ("GHI-9012", "2024-02-27", 98000, "Centro Automotivo Norte",  "Troca de Pneus",   "4 pneus Bridgestone",            3200.0, True, "carlos.silva"),
        ("GHI-9012", "2025-02-05", 110500, "Ford Autorizada Goiania", "Freios",           "Kit freios completo",            1650.0, True, "carlos.silva"),
        ("JKL-3456", "2023-05-20", 120000, "GM Concessionaria GO",    "Revisao Geral",    "Revisao 120 mil km",             2800.0, True, "carlos.silva"),
        ("JKL-3456", "2024-06-15", 143000, "Centro Automotivo Norte", "Eletrica",         "Alternador",                     1900.0, True, "carlos.silva"),
        ("JKL-3456", "2025-01-08", 145500, "Oficina Gilbert Auto",    "Troca de Oleo",    "Troca de oleo 10W40",             290.0, True, "carlos.silva"),
    ]
    c.executemany("INSERT INTO manutencoes (placa, data_servico, km_atual, oficina, tipo_servico, descricao, custo, aceite_lgpd, criado_por) VALUES (?,?,?,?,?,?,?,?,?)", registros)
    conn.commit()
    conn.close()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_login(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, role, display_name FROM users WHERE username=? AND password=?",
              (username.strip(), make_hash(password)))
    result = c.fetchone()
    conn.close()
    return result

def get_all_users():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, username, role, display_name FROM users ORDER BY username", conn)
    conn.close()
    return df

def create_user(username, password, role, display_name):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role, display_name) VALUES (?,?,?,?)",
                  (username.strip(), make_hash(password), role, display_name))
        conn.commit()
        conn.close()
        return True, "Usuario criado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Nome de usuario ja existe."

def delete_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def change_password(username, new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE username=?",
              (make_hash(new_password), username))
    conn.commit()
    conn.close()

TIPOS_SERVICO = [
    "Revisao Geral", "Troca de Oleo", "Troca de Pneus", "Freios",
    "Suspensao", "Alinhamento/Balanceamento", "Ar Condicionado",
    "Eletrica", "Transmissao", "Outros"
]

def get_all_records():
    conn = get_connection()
    query = """
        SELECT m.id, m.placa, v.modelo, v.ano, m.data_servico, m.km_atual, 
               m.oficina, m.tipo_servico, m.descricao, m.custo,
               v.intervalo_km, v.intervalo_meses
        FROM manutencoes m
        JOIN veiculos v ON m.placa = v.placa
        ORDER BY m.data_servico DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_veiculos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM veiculos WHERE ativo=1 ORDER BY placa", conn)
    conn.close()
    return df

# ==========================================
# PÁGINAS DO SISTEMA
# ==========================================
def login_page():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; margin-bottom:20px;'><h1 style='color:#2563eb; font-weight:800; font-size:3rem; margin-bottom:0;'>Logística XYZ</h1><p style='color:#6b7280;'>Sistema Integrado FleetTrace</p></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("👤 Usuario", placeholder="Digite seu usuario")
            passwd = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            submitted = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
            if submitted:
                if user and passwd:
                    result = check_login(user, passwd)
                    if result:
                        st.session_state["logged_in"] = True
                        st.session_state["user_id"] = result[0]
                        st.session_state["username"] = result[1]
                        st.session_state["role"] = result[2]
                        st.session_state["display_name"] = result[3]
                        st.rerun()
                    else:
                        st.error("❌ Credenciais invalidas.")
                else:
                    st.warning("⚠️ Preencha usuario e senha.")
        st.markdown('</div>', unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<div style='padding:10px 0 20px 0;'>"
            "<h2 style='color:#2563eb; font-weight:800; font-size:1.6rem; margin:0;'>Logística XYZ</h2>"
            "<p style='color:#6b7280; font-size:0.8rem; letter-spacing:1px; margin:0;'>Powered by FleetTrace</p>"
            "</div>",
            unsafe_allow_html=True
        )
        role_label = "Administrador" if st.session_state.get("role") == "admin" else "Operador"
        uname = st.session_state.get("display_name", st.session_state.get("username", ""))
        st.markdown(
            f'<div class="user-badge"><span style="font-size:1.5rem">👤</span>'
            f'<div><div style="color:#1f2937;font-weight:700;font-size:0.95rem">{uname}</div>'
            f'<div style="color:#6b7280;font-size:0.8rem">{role_label}</div></div></div>',
            unsafe_allow_html=True
        )
        menu_options = ["📊 Dashboard", "🚗 Frota de Veiculos", "➕ Adicionar Registro", "📋 Consultar / Editar", "🗑️ Excluir Registro"]
        if st.session_state.get("role") == "admin":
            menu_options.append("👥 Gerenciar Usuarios")
        menu = st.radio("Navegacao", menu_options, label_visibility="collapsed")
        
        # Logout button na parte inferior
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            for key in ["logged_in", "username", "user_id", "role", "display_name"]:
                st.session_state.pop(key, None)
            st.rerun()
        return menu

PLOTLY_LIGHT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#1f2937", family="Inter, sans-serif"),
    margin=dict(l=10, r=10, t=30, b=10),
)

def dashboard_view():
    section_header("📊", "Dashboard da Frota", "Analise Geral de Manutencoes")
    df = get_all_records()
    if df.empty:
        st.info("📭 Nenhum registro encontrado na frota.")
        return

    # ---- KPIs ----
    v_df = get_veiculos()
    frota_ativa   = len(v_df)
    custo_total   = df["custo"].sum()
    
    # Calcula a manutencao pendente
    manut_pend = 0
    if not v_df.empty and not df.empty:
        for idx, v in v_df.iterrows():
            ult_manut = df[df["placa"] == v["placa"]]
            if not ult_manut.empty:
                ult = ult_manut.iloc[0]
                km_vencido = ult["km_atual"] >= (ult["km_atual"] + v["intervalo_km"])
                # Como nao temos o KM real atual do carro sem telemetria, assumimos que 
                # se passou o tempo desde a ultima manutencao, esta vencido.
                meses_passados = relativedelta(date.today(), pd.to_datetime(ult["data_servico"]).date()).months
                if meses_passados >= v["intervalo_meses"]:
                    manut_pend += 1

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("🚗", frota_ativa, "Veiculos na Frota")
    with col2:
        render_metric_card("⚠️", manut_pend, "Veiculos Vencidos")
    with col3:
        render_metric_card("💰", f"R$ {custo_total:,.0f}", "Custos Totais")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Gráficos ----
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("##### 🍩 Distribuicao de Custos por Tipo")
        custo_tipo = df.groupby("tipo_servico")["custo"].sum().reset_index()
        custo_tipo.columns = ["Tipo", "Custo"]
        fig1 = go.Figure(go.Pie(
            labels=custo_tipo["Tipo"],
            values=custo_tipo["Custo"],
            hole=0.55,
            textinfo="percent+label",
            marker=dict(colors=px.colors.sequential.Blues_r[:len(custo_tipo)], line=dict(color="#ffffff", width=2)),
            textfont=dict(size=11)
        ))
        fig1.update_layout(**PLOTLY_LIGHT, showlegend=False, height=300,
            annotations=[dict(text=f"<b>R$ {custo_total/1000:.0f}k</b>", x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="#2563eb"))]
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_g2:
        st.markdown("##### 📊 Custo por Veiculo")
        custo_placa = df.groupby(["placa","modelo"])["custo"].sum().reset_index().sort_values("custo", ascending=True)
        custo_placa["label"] = custo_placa["placa"] + " · " + custo_placa["modelo"]
        fig2 = go.Figure(go.Bar(
            x=custo_placa["custo"], y=custo_placa["label"], orientation="h",
            marker=dict(color=custo_placa["custo"], colorscale=[[0,"#93c5fd"],[1,"#2563eb"]]),
            text=[f"R$ {v:,.0f}" for v in custo_placa["custo"]], textposition="outside", textfont=dict(size=10, color="#6b7280")
        ))
        fig2.update_layout(**PLOTLY_LIGHT, height=300, xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, tickfont=dict(size=10)))
        st.plotly_chart(fig2, use_container_width=True)

    # ---- Gráficos de Linha ----
    st.markdown("---")
    col_l1, col_l2 = st.columns(2)
    
    df["mes"] = pd.to_datetime(df["data_servico"]).dt.to_period("M").astype(str)
    
    with col_l1:
        st.markdown("##### 📈 Evolucao Mensal (Total da Frota)")
        custo_mensal = df.groupby("mes")["custo"].sum().reset_index()
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=custo_mensal["mes"], y=custo_mensal["custo"], mode="lines+markers",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(size=7, color="#1d4ed8", line=dict(width=2, color="#ffffff")),
            fill="tozeroy", fillcolor="rgba(37,99,235,0.1)", hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>"
        ))
        fig3.update_layout(**PLOTLY_LIGHT, height=250, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickprefix="R$ "))
        st.plotly_chart(fig3, use_container_width=True)

    with col_l2:
        st.markdown("##### 🏎️ Gastos Individuais por Veiculo")
        df_ind = df.groupby(["mes", "placa"])["custo"].sum().reset_index()
        fig4 = px.line(df_ind, x="mes", y="custo", color="placa", markers=True, color_discrete_sequence=px.colors.qualitative.Set2)
        fig4.update_layout(**PLOTLY_LIGHT, height=250, xaxis_title="", yaxis_title="", 
                           yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickprefix="R$ "),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig4, use_container_width=True)

def frota_view():
    section_header("🚗", "Frota de Veiculos", "Gestao")
    tab1, tab2 = st.tabs(["📋 Lista da Frota", "➕ Gerenciar Veículos"])
    
    with tab1:
        v_df = get_veiculos()
        if v_df.empty:
            st.info("Nenhum veiculo cadastrado.")
        else:
            df = get_all_records()
            st.dataframe(v_df[["placa", "modelo", "ano", "intervalo_km", "intervalo_meses"]], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("##### Adicionar Novo Veiculo")
        with st.form("form_add_veiculo", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            placa = c1.text_input("Placa *").upper()
            modelo = c2.text_input("Modelo *")
            ano = c3.number_input("Ano *", min_value=1990, max_value=2030, step=1, value=2024)
            
            c4, c5 = st.columns(2)
            int_km = c4.number_input("Intervalo de Manutencao (KM) *", min_value=1000, step=1000, value=10000)
            int_mes = c5.number_input("Intervalo de Manutencao (Meses) *", min_value=1, step=1, value=6)
            
            if st.form_submit_button("➕ Salvar Veiculo", type="primary"):
                if placa and modelo:
                    conn = get_connection()
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO veiculos (placa, modelo, ano, intervalo_km, intervalo_meses) VALUES (?,?,?,?,?)",
                                  (placa, modelo, ano, int_km, int_mes))
                        conn.commit()
                        st.success("Veiculo cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Placa ja cadastrada!")
                    finally:
                        conn.close()
                else:
                    st.error("Preencha os campos obrigatorios!")
        
        st.markdown("---")
        st.markdown("##### Excluir Veiculo")
        if not v_df.empty:
            del_placa = st.selectbox("Selecione o veiculo para remover:", v_df["placa"].tolist())
            if st.button("🗑️ Remover Veiculo"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM veiculos WHERE placa=?", (del_placa,))
                conn.commit()
                conn.close()
                st.success("Veiculo removido! Atualize a pagina para ver os efeitos.")

def adicionar_view():
    section_header("➕", "Adicionar Registro", "Nova Manutencao")
    v_df = get_veiculos()
    if v_df.empty:
        st.warning("Cadastre um veiculo na Frota primeiro!")
        return

    placas_dict = {row["placa"]: f"{row['placa']} - {row['modelo']}" for _, row in v_df.iterrows()}
    
    with st.form("form_add"):
        col1, col2 = st.columns(2)
        placa = col1.selectbox("Veiculo *", options=list(placas_dict.keys()), format_func=lambda x: placas_dict[x])
        data_serv = col2.date_input("Data do Servico *", value=date.today())
        
        col3, col4, col5 = st.columns(3)
        km = col3.number_input("KM Atual do Veiculo *", min_value=0, step=100)
        oficina = col4.text_input("Oficina / Fornecedor *")
        tipo = col5.selectbox("Tipo de Servico *", TIPOS_SERVICO)
        
        desc = st.text_area("Descricao Detalhada do Servico")
        custo = st.number_input("Custo Total (R$) *", min_value=0.0, step=10.0, format="%.2f")
        aceite = st.checkbox("Aceito os termos da LGPD e autorizo o armazenamento destes dados.", value=True)
        
        if st.form_submit_button("💾 Salvar Registro", type="primary", use_container_width=True):
            if not placa or not oficina or custo <= 0 or not km:
                st.error("❌ Preencha todos os campos obrigatorios marcados com *")
            elif not aceite:
                st.error("❌ E obrigatorio aceitar os termos da LGPD.")
            else:
                conn = get_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO manutencoes 
                    (placa, data_servico, km_atual, oficina, tipo_servico, descricao, custo, aceite_lgpd, criado_por) 
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (placa, data_serv, km, oficina, tipo, desc, custo, aceite, st.session_state.get("username")))
                conn.commit()
                conn.close()
                st.success("✅ Registro adicionado com sucesso!")

def consultar_editar_view():
    section_header("📋", "Consultar e Editar", "Busca de Registros")
    df = get_all_records()
    if df.empty:
        st.info("Nenhum registro para consultar.")
        return
        
    pesquisa = st.text_input("🔍 Buscar por Placa ou Modelo:", placeholder="Ex: ABC-1234")
    if pesquisa:
        df = df[df["placa"].str.contains(pesquisa, case=False) | df["modelo"].str.contains(pesquisa, case=False)]
        
    st.dataframe(df[["id", "placa", "modelo", "data_servico", "tipo_servico", "custo", "oficina"]], use_container_width=True, hide_index=True)

def excluir_view():
    section_header("🗑️", "Excluir Registro", "Remocao de Dados")
    df = get_all_records()
    if df.empty:
        st.info("Nenhum registro disponivel.")
        return
        
    df["display_label"] = df["placa"] + " - " + df["tipo_servico"] + " em " + df["data_servico"] + " (R$ " + df["custo"].astype(str) + ")"
    label_dict = dict(zip(df["id"], df["display_label"]))
    
    registro_id = st.selectbox("Selecione o registro para excluir", df["id"].tolist(), format_func=lambda x: label_dict[x])
    if st.button("Excluir Definitivamente", type="primary"):
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM manutencoes WHERE id=?", (registro_id,))
        conn.commit()
        conn.close()
        st.success("Registro excluido com sucesso.")

def usuarios_view():
    section_header("👥", "Gerenciar Usuarios", "Controle de Acesso")
    st.dataframe(get_all_users(), use_container_width=True, hide_index=True)

def main():
    init_db()
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        login_page()
    else:
        menu = render_sidebar()
        if menu == "📊 Dashboard": dashboard_view()
        elif menu == "🚗 Frota de Veiculos": frota_view()
        elif menu == "➕ Adicionar Registro": adicionar_view()
        elif menu == "📋 Consultar / Editar": consultar_editar_view()
        elif menu == "🗑️ Excluir Registro": excluir_view()
        elif menu == "👥 Gerenciar Usuarios": usuarios_view()

if __name__ == "__main__":
    main()
