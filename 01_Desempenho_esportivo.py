import streamlit as st
import pandas as pd
import plotly.express as px

# =========================

# CONFIGURAÇÃO DA PÁGINA

# =========================

st.set_page_config(
page_title="Desempenho Esportivo",
page_icon="⚽",
layout="wide"
)

st.title("⚽ Desempenho Esportivo")
st.write(
"Compare os clubes e descubra como o desempenho "
"de cada equipe evoluiu ao longo das temporadas."
)

# =========================

# CARREGAMENTO DOS DADOS

# =========================

df = pd.read_csv("Tabela_Clubes.csv")

# Separar gols feitos e sofridos

gols = df["GolsF/S"].astype(str).str.split(":", expand=True)

df["Gols_Feitos"] = pd.to_numeric(gols[0], errors="coerce")
df["Gols_Sofridos"] = pd.to_numeric(gols[1], errors="coerce")

# Calcular saldo de gols

df["Saldo_Gols"] = df["Gols_Feitos"] - df["Gols_Sofridos"]

# Converter posição para número

df["Pos."] = pd.to_numeric(df["Pos."], errors="coerce")

# Converter ano para número, quando possível

df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce")

# =========================

# FILTROS

# =========================

st.sidebar.header("Filtros")

clubes = sorted(df["Clubes"].dropna().unique().tolist())

clubes_selecionados = st.sidebar.multiselect(
"Selecione os clubes",
options=clubes,
default=clubes[:1]
)

anos = sorted(df["Ano"].dropna().unique().tolist())

anos_selecionados = st.sidebar.multiselect(
"Selecione as temporadas",
options=anos,
default=anos
)

# Aplicar os filtros

df_filtrado = df[
df["Clubes"].isin(clubes_selecionados)
& df["Ano"].isin(anos_selecionados)
].copy()

df_filtrado = df_filtrado.sort_values("Ano")

# =========================

# VALIDAÇÃO DOS FILTROS

# =========================

if not clubes_selecionados:
    st.info("Selecione pelo menos um clube na barra lateral.")

elif not anos_selecionados:
    st.info("Selecione pelo menos uma temporada.")

elif df_filtrado.empty:
    st.warning("Não existem dados para os filtros selecionados.")

else:
 
# =========================
# INDICADORES GERAIS
# =========================

    st.subheader("📊 Resumo do desempenho")

col1, col2, col3 = st.columns(3)

with col1:
    gols_feitos = df_filtrado["Gols_Feitos"].sum()
    st.metric(
        "Total de gols feitos",
        f"{gols_feitos:,.0f}".replace(",", ".")
    )

with col2:
    gols_sofridos = df_filtrado["Gols_Sofridos"].sum()
    st.metric(
        "Total de gols sofridos",
        f"{gols_sofridos:,.0f}".replace(",", ".")
    )

with col3:
    saldo_gols = df_filtrado["Saldo_Gols"].sum()
    st.metric(
        "Saldo total de gols",
        f"{saldo_gols:+,.0f}".replace(",", ".")
    )

st.caption(
    "Os indicadores somam os resultados de todos os clubes "
    "e temporadas selecionados."
)

# =========================
# EVOLUÇÃO DA CLASSIFICAÇÃO
# =========================

st.subheader("🏆 Evolução na classificação")

dados_posicao = df_filtrado.dropna(subset=["Pos."])

if not dados_posicao.empty:

    grafico_posicao = px.line(
        dados_posicao,
        x="Ano",
        y="Pos.",
        color="Clubes",
        markers=True,
        title="Posição de cada clube por temporada",
        labels={
            "Ano": "Temporada",
            "Pos.": "Posição na tabela",
            "Clubes": "Clube"
        },
        hover_data=["Gols_Feitos", "Gols_Sofridos", "Saldo_Gols"]
    )

    # Posição 1 aparece no topo
    grafico_posicao.update_yaxes(autorange="reversed")

    st.plotly_chart(
        grafico_posicao,
        use_container_width=True
    )

else:
    st.info("Não existem posições válidas para exibir.")

# =========================
# COMPARAÇÃO DE GOLS
# =========================

st.subheader("⚽ Gols feitos e sofridos")

dados_gols = df_filtrado.melt(
    id_vars=["Ano", "Clubes"],
    value_vars=["Gols_Feitos", "Gols_Sofridos"],
    var_name="Tipo",
    value_name="Quantidade"
)

dados_gols["Tipo"] = dados_gols["Tipo"].replace({
    "Gols_Feitos": "Gols feitos",
    "Gols_Sofridos": "Gols sofridos"
})

grafico_gols = px.bar(
    dados_gols,
    x="Ano",
    y="Quantidade",
    color="Tipo",
    barmode="group",
    facet_col="Clubes",
    facet_col_wrap=2,
    title="Comparação de gols por temporada",
    labels={
        "Ano": "Temporada",
        "Quantidade": "Número de gols",
        "Tipo": "Tipo de gol",
        "Clubes": "Clube"
    }
)

grafico_gols.update_layout(
    showlegend=True
)

st.plotly_chart(
    grafico_gols,
    use_container_width=True
)

# =========================
# SALDO DE GOLS
# =========================

st.subheader("📈 Evolução do saldo de gols")

grafico_saldo = px.line(
    df_filtrado,
    x="Ano",
    y="Saldo_Gols",
    color="Clubes",
    markers=True,
    title="Saldo de gols por temporada",
    labels={
        "Ano": "Temporada",
        "Saldo_Gols": "Saldo de gols",
        "Clubes": "Clube"
    }
)

grafico_saldo.add_hline(
    y=0,
    line_dash="dash",
    line_color="gray"
)

st.plotly_chart(
    grafico_saldo,
    use_container_width=True
)

# =========================
# TABELA DE DESEMPENHO
# =========================

st.subheader("📋 Histórico dos clubes")

st.dataframe(
    df_filtrado[
        [
            "Ano",
            "Clubes",
            "Pos.",
            "Gols_Feitos",
            "Gols_Sofridos",
            "Saldo_Gols"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

