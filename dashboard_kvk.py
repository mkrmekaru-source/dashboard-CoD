import os
import glob
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px

# --- FORÇA O TEMA ESCURO NO STREAMLIT ---
os.makedirs('.streamlit', exist_ok=True)
with open('.streamlit/config.toml', 'w') as f:
    f.write('[theme]\nbase="dark"\n')
# ----------------------------------------

st.set_page_config(page_title="Dashboard KvK - Call of Dragons", layout="wide")

# --- AJUSTA A ESCALA GERAL DA PÁGINA PARA 85% ---
st.markdown(
    """
    <style>
        .stApp {
            zoom: 0.85;
            -moz-transform: scale(0.85);
            -moz-transform-origin: 0 0;
        }
    </style>
    """,
    unsafe_allow_html=True
)

def traduzir_data_arquivo(nome_arquivo):
    try:
        nome_base = os.path.basename(nome_arquivo)
        timestamp = int(nome_base.split('_')[2].split('.')[0]) / 1000000
        data = datetime.datetime.fromtimestamp(timestamp)
        return data.strftime('%d/%m/%Y às %H:%M')
    except:
        return os.path.basename(nome_arquivo)

@st.cache_data
def carregar_dados(file_start, file_end):
    if not file_start or not file_end:
        return pd.DataFrame()
    
    df_start = pd.read_excel(file_start)
    df_end = pd.read_excel(file_end)
    
    df_merged = pd.merge(df_start, df_end, on='lord_id', suffixes=('_start', '_end'))
    
    df_merged['Nome'] = df_merged['name_end'].fillna('Desconhecido').astype(str)
    df_merged['Servidor'] = df_merged['home_server_end'].fillna('0').astype(int).astype(str)
    
    # Identificação da aliança
    alianca_final = df_merged['alliance_tag_end'].fillna('').astype(str).str.strip()
    alianca_inicial = df_merged['alliance_tag_start'].fillna('').astype(str).str.strip() if 'alliance_tag_start' in df_merged.columns else pd.Series(['']*len(df_merged))
    
    df_merged['Aliança'] = alianca_final
    df_merged.loc[(df_merged['Aliança'] == '') | (df_merged['Aliança'] == '0') | (df_merged['Aliança'] == 'nan'), 'Aliança'] = alianca_inicial[
        (alianca_inicial != '') & (alianca_inicial != '0') & (alianca_inicial != 'nan')
    ]
    df_merged['Aliança'] = df_merged['Aliança'].replace({'': 'Sem Aliança', '0': 'Sem Aliança', 'nan': 'Sem Aliança'})
    
    colunas_para_zerar = [
        'power_start', 'power_end',
        'units_killed_start', 'units_killed_end',
        'units_dead_start', 'units_dead_end',
        'merits_start', 'merits_end',
        'units_healed_start', 'units_healed_end',
        'wood_start', 'wood_end',
        'gold_start', 'gold_end',
        'ore_start', 'ore_end',
        'mana_start', 'mana_end',
        'helps_given_start', 'helps_given_end',
        'resources_given_start', 'resources_given_end'
    ]
    
    for col in colunas_para_zerar:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

    df_merged['power_diff'] = df_merged['power_end'] - df_merged['power_start']
    df_merged['kills_gained'] = df_merged['units_killed_end'] - df_merged['units_killed_start']
    df_merged['dead_gained'] = df_merged['units_dead_end'] - df_merged['units_dead_start']
    df_merged['merits_gained'] = df_merged['merits_end'] - df_merged['merits_start']
    df_merged['healed_gained'] = df_merged['units_healed_end'] - df_merged['units_healed_start']
    
    df_merged['wood_gained'] = df_merged['wood_end'] - df_merged['wood_start']
    df_merged['gold_gained'] = df_merged['gold_end'] - df_merged['gold_start']
    df_merged['ore_gained'] = df_merged['ore_end'] - df_merged['ore_start']
    df_merged['mana_gained'] = df_merged['mana_end'] - df_merged['mana_start']
    
    df_merged['helps_gained'] = df_merged['helps_given_end'] - df_merged['helps_given_start']
    df_merged['resources_donated_gained'] = df_merged['resources_given_end'] - df_merged['resources_given_start']

    return df_merged

def renderizar_celula_poder(base, delta):
    try:
        b = float(base)
        d = float(delta)
        if d == 0:
            return f"{b:,.0f}"
        elif d > 0:
            return f"{b:,.0f} (+{d:,.0f})"
        else:
            return f"{b:,.0f} ({d:,.0f})"
    except:
        return "0"

def renderizar_apenas_delta(delta):
    try:
        d = float(delta)
        if d == 0:
            return "0"
        elif d > 0:
            return f"+{d:,.0f}"
        else:
            return f"{d:,.0f}"
    except:
        return "0"

def formata_br(val):
    try:
        return f"{int(val):,}".replace(",", ".")
    except:
        return str(val)

# --- FUNÇÃO OTIMIZADA PARA RENDERIZAR OS TOP 15 NA WEB ---
def renderizar_graficos_top15(df_plot, sufixo_titulo=""):
    if df_plot is None or df_plot.empty:
        st.info(f"Sem dados suficientes para exibir os gráficos {sufixo_titulo}.")
        return

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"### 📈 Ranking Top 15 Jogadores {sufixo_titulo}")
    
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    c5, _ = st.columns(2)
    
    graficos_config = [
        ("merits_gained", "Top 15 - Méritos Obtidos", "Blues", c1),
        ("dead_gained", "Top 15 - Tropas Mortas (Baixas Definitivas)", "Greys", c2),
        ("healed_gained", "Top 15 - Tropas Curadas", "Greens", c3),
        ("kills_gained", "Top 15 - Kills (Inimigos)", "Reds", c4),
        ("mana_gained", "Top 15 - Mana Coletada", "Purples", c5),
    ]
    
    for metrica, titulo, escala_cor, coluna_layout in graficos_config:
        if metrica not in df_plot.columns:
            continue
            
        dados = df_plot.copy()
        dados[metrica] = pd.to_numeric(dados[metrica], errors='coerce').fillna(0)
        top15 = dados.sort_values(by=metrica, ascending=False).head(15).copy()
        top15['Nome'] = top15['Nome'].astype(str)
        top15['texto_bar'] = top15[metrica].apply(formata_br)
        
        fig = px.bar(
            top15,
            x=metrica,
            y='Nome',
            orientation='h',
            title=titulo,
            color=metrica,
            color_continuous_scale=escala_cor,
            template="plotly_dark",
            text='texto_bar'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            margin=dict(l=20, r=30, t=40, b=20)
        )
        coluna_layout.plotly_chart(fig, use_container_width=True)

st.title("⚔️ Dashboard Interativo - KvK")

# =====================================================================
# BUSCA AUTOMÁTICA DE ARQUIVOS EXCEL NO REPOSITÓRIO DO GITHUB
# =====================================================================
arquivos = sorted(glob.glob("**/kvk_*.xlsx", recursive=True) + glob.glob("kvk_*.xlsx"))
arquivos = sorted(list(set(arquivos)))

if len(arquivos) < 2:
    arquivos = sorted(glob.glob("**/*.xlsx", recursive=True) + glob.glob("*.xlsx"))
    arquivos = sorted(list(set(arquivos)))

if len(arquivos) < 2:
    st.error("⚠️ Você precisa subir pelo menos 2 arquivos Excel (.xlsx) no repositório do GitHub para realizar as comparações.")
else:
    st.sidebar.header("Filtros e Configurações")
    
    opcoes_modo = [
        "🏆 Período Completo (Primeiro vs Último)",
        "⚡ Última Variação (Penúltimo vs Último)",
        "⚙️ Personalizado (Escolher Datas)"
    ]
    modo_selecionado = st.sidebar.selectbox("Modo de Comparação:", opcoes_modo)
    
    if modo_selecionado == opcoes_modo[0]:
        file_start = arquivos[0]
        file_end = arquivos[-1]
    elif modo_selecionado == opcoes_modo[1]:
        file_start = arquivos[-2]
        file_end = arquivos[-1]
    else:
        dict_datas = {traduzir_data_arquivo(f): f for f in arquivos}
        lista_datas = list(dict_datas.keys())
        
        sel_inicio = st.sidebar.selectbox("Arquivo Inicial:", lista_datas, index=0)
        sel_fim = st.sidebar.selectbox("Arquivo Final:", lista_datas, index=len(lista_datas)-1)
        
        file_start = dict_datas[sel_inicio]
        file_end = dict_datas[sel_fim]

    data_inicio = traduzir_data_arquivo(file_start)
    data_fim = traduzir_data_arquivo(file_end)
    st.sidebar.markdown(f"**Comparando:**\n\n🟢 {data_inicio}\n\n🔴 {data_fim}")
    st.sidebar.divider()

    df = carregar_dados(file_start, file_end)

    servidores = ["Todos"] + sorted([str(x) for x in df['Servidor'].unique() if str(x) != '0'])
    servidor_selecionado = st.sidebar.selectbox("Filtrar por Servidor:", servidores)
    
    busca_nome = st.sidebar.text_input("Buscar Jogador (Nome):", "")

    ordem_opcoes = {
        "Poder (Maior para Menor)": "power_end",
        "Mortes (Maior para Menor)": "dead_gained",
        "Méritos Ganhos (Maior para Menor)": "merits_gained",
        "Kills (Inimigos) (Maior para Menor)": "kills_gained",
        "Curadas (Maior para Menor)": "healed_gained",
        "Mana (Maior para Menor)": "mana_gained",
        "Madeira (Maior para Menor)": "wood_gained",
        "Ouro (Maior para Menor)": "gold_gained",
        "Minério (Maior para Menor)": "ore_gained",
        "Ajudas (Maior para Menor)": "helps_gained",
        "Doações (Maior para Menor)": "resources_donated_gained"
    }
    ordem_selecionada = st.sidebar.selectbox("Ordenar Tabela por:", list(ordem_opcoes.keys()))
    chave_ativa = ordem_opcoes[ordem_selecionada]

    df_filtrado = df.copy()
    if servidor_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Servidor'] == servidor_selecionado]
    if busca_nome:
        df_filtrado = df_filtrado[df_filtrado['Nome'].str.contains(busca_nome, case=False, na=False)]

    df_filtrado = df_filtrado.sort_values(by=chave_ativa, ascending=False)
    df_filtrado['Posicao'] = range(1, len(df_filtrado) + 1)

    total_madeira = df_filtrado['wood_gained'].sum()
    total_ouro = df_filtrado['gold_gained'].sum()
    total_minerio = df_filtrado['ore_gained'].sum()

    soma_recursos = total_madeira + total_ouro + total_minerio
    
    if soma_recursos > 0:
        pct_madeira = (total_madeira / soma_recursos) * 100
        pct_ouro = (total_ouro / soma_recursos) * 100
        pct_minerio = (total_minerio / soma_recursos) * 100
    else:
        pct_madeira = pct_ouro = pct_minerio = 0.0

    st.markdown(f"### Resumo do Período ({modo_selecionado.split(' ')[1]} {modo_selecionado.split(' ')[2]})")
    
    r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
    r1_col1.metric("Poder Total Atual", f"{df_filtrado['power_end'].sum():,.0f}", f"{df_filtrado['power_diff'].sum():,.0f}")
    r1_col2.metric("Kills Adicionais", f"{df_filtrado['kills_gained'].sum():,.0f}")
    r1_col3.metric("Tropas Mortas", f"{df_filtrado['dead_gained'].sum():,.0f}")
    r1_col4.metric("Méritos Obtidos", f"{df_filtrado['merits_gained'].sum():,.0f}")

    r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
    r2_col1.metric("Tropas Curadas", f"{df_filtrado['healed_gained'].sum():,.0f}")
    r2_col2.metric("Mana Coletada", f"{df_filtrado['mana_gained'].sum():,.0f}")
    r2_col3.metric("Madeira Coletada", f"{total_madeira:,.0f}", f"{pct_madeira:.1f}% do total")
    r2_col4.metric("Ouro Coletado", f"{total_ouro:,.0f}", f"{pct_ouro:.1f}% do total")

    r3_col1, r3_col2, r3_col3, r3_col4 = st.columns(4)
    r3_col1.metric("Minério Coletado", f"{total_minerio:,.0f}", f"{pct_minerio:.1f}% do total")
    r3_col2.metric("Ajudas Realizadas", f"{df_filtrado['helps_gained'].sum():,.0f}")
    r3_col3.metric("Doações de Recursos", f"{df_filtrado['resources_donated_gained'].sum():,.0f}")
    r3_col4.empty()

    st.divider()

    st.markdown("### 📊 Tabela de Variações do Período (DKP)")

    total_linhas = len(df_filtrado)
    
    col_pag1, col_pag2 = st.columns([2, 5])
    with col_pag1:
        linhas_por_pagina = st.selectbox("Registros por Página:", [10, 25, 50, 100, 200], index=0)
        
    total_paginas = max(1, (total_linhas + linhas_por_pagina - 1) // linhas_por_pagina)

    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 1

    if st.session_state.pagina_atual > total_paginas:
        st.session_state.pagina_atual = total_paginas

    with col_pag2:
        st.markdown(f"<div style='padding-top: 25px; font-weight: bold;'>Página {st.session_state.pagina_atual} de {total_paginas} (Total de Registros: {total_linhas})</div>", unsafe_allow_html=True)

    b_col1, b_col2, b_col3, b_col4, _ = st.columns([1, 1, 1, 1, 6])
    with b_col1:
        if st.button("<< Início"):
            st.session_state.pagina_atual = 1
            st.rerun()
    with b_col2:
        if st.button("< Anterior"):
            if st.session_state.pagina_atual > 1:
                st.session_state.pagina_atual -= 1
                st.rerun()
    with b_col3:
        if st.button("Próxima >"):
            if st.session_state.pagina_atual < total_paginas:
                st.session_state.pagina_atual += 1
                st.rerun()
    with b_col4:
        if st.button("Fim >>"):
            st.session_state.pagina_atual = total_paginas
            st.rerun()

    inicio_idx = (st.session_state.pagina_atual - 1) * linhas_por_pagina
    fim_idx = min(inicio_idx + linhas_por_pagina, total_linhas)
    df_pagina = df_filtrado.iloc[inicio_idx:fim_idx]

    colunas_info = [
        {"nome": "Pos.", "chave": "Posicao", "tipo": "texto"},
        {"nome": "Servidor", "chave": "Servidor", "tipo": "texto"},
        {"nome": "Aliança", "chave": "Aliança", "tipo": "texto"},
        {"nome": "Nome", "chave": "Nome", "tipo": "texto"},
        {"nome": "Poder", "chave": "power_end", "tipo": "poder"},
        {"nome": "Mortes", "chave": "dead_gained", "tipo": "delta"},
        {"nome": "Méritos", "chave": "merits_gained", "tipo": "delta"},
        {"nome": "Kills (Inimigos)", "chave": "kills_gained", "tipo": "delta"},
        {"nome": "Curadas", "chave": "healed_gained", "tipo": "delta"},
        {"nome": "Mana", "chave": "mana_gained", "tipo": "delta"},
        {"nome": "Madeira", "chave": "wood_gained", "tipo": "delta"},
        {"nome": "Ouro", "chave": "gold_gained", "tipo": "delta"},
        {"nome": "Minério", "chave": "ore_gained", "tipo": "delta"},
        {"nome": "Ajudas", "chave": "helps_gained", "tipo": "delta"},
        {"nome": "Doações", "chave": "resources_donated_gained", "tipo": "delta"}
    ]

    html_table = """
    <style>
        .custom-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; color: white; background-color: #0e1117; white-space: nowrap; }
        .custom-table th { background-color: #262730; padding: 10px 15px; text-align: center; border-bottom: 2px solid #444; }
        .custom-table td { padding: 10px 15px; text-align: center; border-bottom: 1px solid #333; color: white; }
        .custom-table th:nth-child(1), .custom-table td:nth-child(1) { text-align: center; color: #4da6ff; font-weight: bold; }
        .custom-table th:nth-child(2), .custom-table td:nth-child(2),
        .custom-table th:nth-child(3), .custom-table td:nth-child(3),
        .custom-table th:nth-child(4), .custom-table td:nth-child(4) { text-align: left; }
        .custom-table tr:hover { background-color: #1a1c23; }
        .scrollable-container { overflow-x: auto; width: 100%; margin-top: 10px; }
        
        .destaque-header { background-color: #1f3a5f !important; color: #4da6ff !important; border-bottom: 3px solid #4da6ff !important; font-weight: bold; }
        .destaque-body { background-color: #132238 !important; color: #70a1ff !important; font-weight: bold; }
    </style>
    <div class="scrollable-container">
    <table class="custom-table">
        <thead>
            <tr>
    """
    
    for col in colunas_info:
        if col["chave"] == chave_ativa:
            html_table += f'<th class="destaque-header">{col["nome"]} ★</th>'
        else:
            html_table += f'<th>{col["nome"]}</th>'
            
    html_table += "</tr></thead><tbody>"
    
    for index, row in df_pagina.iterrows():
        html_table += "<tr>"
        for col in colunas_info:
            classe_destaque = ' class="destaque-body"' if col["chave"] == chave_ativa else ''
            
            if col["tipo"] == "texto":
                val = row[col["chave"]]
                if col["chave"] == "Posicao":
                    val = f"{val}º"
            elif col["tipo"] == "poder":
                val = renderizar_celula_poder(row['power_end'], row['power_diff'])
            else:
                val = renderizar_apenas_delta(row[col["chave"]])
                
            html_table += f'<td{classe_destaque}>{val}</td>'
        html_table += "</tr>"
        
    html_table += "</tbody></table></div>"

    st.markdown(html_table, unsafe_allow_html=True)
    renderizar_graficos_top15(df_filtrado, "(Geral)")

    # ===============================================================================================
    # TABELA EXCLUSIVA PARA JOGADORES BRASILEIROS
    # ===============================================================================================
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🇧🇷 Dashboard Exclusivo - Brasileiros (BRs)")
    
    lista_br_ids = [
        11851349, 8049572, 11869725, 2354626, 13054948, 
        4183516, 22212874, 705090, 5654713, 11811336, 
        489144, 7558106, 11788501, 948759, 1187097
    ]
    
    df_br = df[df['lord_id'].isin(lista_br_ids)].copy()
    ids_encontrados = df['lord_id'].tolist()
    ids_ausentes = [str(br_id) for br_id in lista_br_ids if br_id not in ids_encontrados]
    
    if ids_ausentes:
        st.warning(f"⚠️ Atenção: Os seguintes IDs não foram encontrados no relatório atual: **{', '.join(ids_ausentes)}**")
    
    if not df_br.empty:
        df_br = df_br.sort_values(by=chave_ativa, ascending=False)
        df_br['Posicao'] = range(1, len(df_br) + 1)
        
        total_madeira_br = df_br['wood_gained'].sum()
        total_ouro_br = df_br['gold_gained'].sum()
        total_minerio_br = df_br['ore_gained'].sum()

        soma_recursos_br = total_madeira_br + total_ouro_br + total_minerio_br
        
        if soma_recursos_br > 0:
            pct_madeira_br = (total_madeira_br / soma_recursos_br) * 100
            pct_ouro_br = (total_ouro_br / soma_recursos_br) * 100
            pct_minerio_br = (total_minerio_br / soma_recursos_br) * 100
        else:
            pct_madeira_br = pct_ouro_br = pct_minerio_br = 0.0

        st.markdown(f"#### Resumo da Equipe BR ({modo_selecionado.split(' ')[1]} {modo_selecionado.split(' ')[2]})")
        
        r1_br_col1, r1_br_col2, r1_br_col3, r1_br_col4 = st.columns(4)
        r1_br_col1.metric("Poder Total (BR)", f"{df_br['power_end'].sum():,.0f}", f"{df_br['power_diff'].sum():,.0f}")
        r1_br_col2.metric("Kills Adicionais (BR)", f"{df_br['kills_gained'].sum():,.0f}")
        r1_br_col3.metric("Tropas Mortas (BR)", f"{df_br['dead_gained'].sum():,.0f}")
        r1_br_col4.metric("Méritos Obtidos (BR)", f"{df_br['merits_gained'].sum():,.0f}")

        r2_br_col1, r2_br_col2, r2_br_col3, r2_br_col4 = st.columns(4)
        r2_br_col1.metric("Tropas Curadas (BR)", f"{df_br['healed_gained'].sum():,.0f}")
        r2_br_col2.metric("Mana Coletada (BR)", f"{df_br['mana_gained'].sum():,.0f}")
        r2_br_col3.metric("Madeira Coletada (BR)", f"{total_madeira_br:,.0f}", f"{pct_madeira_br:.1f}% do total")
        r2_br_col4.metric("Ouro Coletado (BR)", f"{total_ouro_br:,.0f}", f"{pct_ouro_br:.1f}% do total")

        r3_br_col1, r3_br_col2, r3_br_col3, r3_br_col4 = st.columns(4)
        r3_br_col1.metric("Minério Coletado (BR)", f"{total_minerio_br:,.0f}", f"{pct_minerio_br:.1f}% do total")
        r3_br_col2.metric("Ajudas Realizadas (BR)", f"{df_br['helps_gained'].sum():,.0f}")
        r3_br_col3.metric("Doações de Recursos (BR)", f"{df_br['resources_donated_gained'].sum():,.0f}")
        r3_br_col4.empty()
        
        st.markdown("<br>", unsafe_allow_html=True)

        html_table_br = """
        <div class="scrollable-container">
        <table class="custom-table">
            <thead>
                <tr>
        """
        
        for col in colunas_info:
            if col["chave"] == chave_ativa:
                html_table_br += f'<th class="destaque-header">{col["nome"]} ★</th>'
            else:
                html_table_br += f'<th>{col["nome"]}</th>'
                
        html_table_br += "</tr></thead><tbody>"
        
        for index, row in df_br.iterrows():
            html_table_br += "<tr>"
            for col in colunas_info:
                classe_destaque = ' class="destaque-body"' if col["chave"] == chave_ativa else ''
                
                if col["tipo"] == "texto":
                    val = row[col["chave"]]
                    if col["chave"] == "Posicao":
                        val = f"{val}º"
                elif col["tipo"] == "poder":
                    val = renderizar_celula_poder(row['power_end'], row['power_diff'])
                else:
                    val = renderizar_apenas_delta(row[col["chave"]])
                    
                html_table_br += f'<td{classe_destaque}>{val}</td>'
            html_table_br += "</tr>"
            
        html_table_br += "</tbody></table></div>"
        
        st.markdown(html_table_br, unsafe_allow_html=True)
        renderizar_graficos_top15(df_br, "(Equipe BR)")
        
    else:
        st.info("Nenhum jogador brasileiro foi encontrado nos arquivos selecionados.")
