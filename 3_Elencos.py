import re

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Perfil dos Elencos",
    page_icon="👥",
    layout="wide",
)

MENSAGEM_SEM_REGISTROS = (
    "Não há registros para essa seleção. O clube pode não ter disputado "
    "a Série A nessa temporada ou os dados podem estar ausentes da base."
)
SEM_CLUBE = "⟨Sem clube⟩"
SEM_TEMPORADA = "⟨Sem temporada⟩"


def carregar_dados():
    """Lê o CSV e apresenta um aviso amigável se o arquivo não estiver no local esperado."""
    try:
        dados = pd.read_csv("Tabela_Clubes.csv")
    except FileNotFoundError:
        st.error(
            "Não encontrei o arquivo 'Tabela_Clubes.csv'. "
            "Deixe esse CSV na pasta principal do projeto, junto do arquivo Inicio.py."
        )
        st.stop()
    except pd.errors.EmptyDataError:
        st.error("O arquivo 'Tabela_Clubes.csv' está vazio.")
        st.stop()
    except (pd.errors.ParserError, UnicodeDecodeError) as erro:
        st.error(
            "Não consegui ler o CSV. Confira se ele está salvo como CSV válido. "
            f"Detalhe: {erro}"
        )
        st.stop()

    dados.columns = dados.columns.astype(str).str.strip()
    colunas_obrigatorias = ["Ano", "Clubes"]
    faltantes = [col for col in colunas_obrigatorias if col not in dados.columns]
    if faltantes:
        st.error(
            "O CSV precisa ter as colunas 'Ano' e 'Clubes'. "
            "Colunas ausentes: " + ", ".join(faltantes)
        )
        st.stop()

    return dados


def limpar_texto(valor):
    if pd.isna(valor):
        return pd.NA
    texto = str(valor).strip()
    return texto if texto else pd.NA


def normalizar_ano(valor):
    """Transforma valores como 2011.0 ou 'Temporada 2011' em '2011'."""
    texto = limpar_texto(valor)
    if pd.isna(texto):
        return pd.NA
    encontrado = re.search(r"\d{4}", str(texto))
    return encontrado.group(0) if encontrado else str(texto)


def ordenar_ano(ano):
    encontrado = re.search(r"\d{4}", str(ano))
    if encontrado:
        return (0, int(encontrado.group(0)), str(ano))
    return (1, 9999, str(ano))


def converter_numero(valor):
    """Aceita números comuns e formatos como 23,1, 1.234,56 e valores com R$."""
    if pd.isna(valor):
        return float("nan")

    texto = str(valor).strip()
    if texto.lower() in {"", "nan", "none", "<na>"}:
        return float("nan")

    texto = (
        texto.replace("R$", "")
        .replace("$", "")
        .replace("€", "")
        .replace("%", "")
        .replace("**", "")
        .replace(" ", "")
    )
    texto = re.sub(r"[^\d,\.\-+]", "", texto)
    if not texto:
        return float("nan")

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif texto.count(",") > 1:
        texto = texto.replace(",", "")
    elif "," in texto:
        if re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+", texto):
            texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")
    elif texto.count(".") > 1:
        texto = texto.replace(".", "")
    elif re.fullmatch(r"[+-]?\d{1,3}\.\d{3}", texto):
        texto = texto.replace(".", "")

    return pd.to_numeric(texto, errors="coerce")


def formatar_numero(valor, casas=1):
    if pd.isna(valor):
        return "Sem dados"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def mostrar_aviso_sem_registros():
    st.info(MENSAGEM_SEM_REGISTROS)
    st.stop()


st.title("👥 Perfil dos Elencos")
st.write(
    "Analise a idade média, a presença de jogadores estrangeiros e o valor "
    "dos elencos registrados em cada temporada. Use os filtros para comparar clubes."
)

# =========================
# CARREGAMENTO E PREPARAÇÃO
# =========================
df = carregar_dados()

# Padroniza os identificadores sem apagar as linhas que possam ter dados ausentes.
df["Ano"] = df["Ano"].apply(normalizar_ano).astype("string")
df["Clubes"] = df["Clubes"].apply(limpar_texto).astype("string")
df = df.replace(r"^\s*$", pd.NA, regex=True)

# Cria rótulos específicos para os filtros, permitindo encontrar linhas sem clube/ano.
df["_AnoFiltro"] = df["Ano"].fillna(SEM_TEMPORADA).astype(str)
df["_ClubeFiltro"] = df["Clubes"].fillna(SEM_CLUBE).astype(str)
df["_ClubeExibicao"] = df["Clubes"].fillna(SEM_CLUBE).astype(str)
df["_AnoExibicao"] = df["Ano"].fillna(SEM_TEMPORADA).astype(str)

# Converte apenas as métricas usadas nesta página; colunas ausentes viram NaN.
for coluna in ["Idade_Media", "Estrangeiros", "Valor_total", "Pos."]:
    if coluna in df.columns:
        df[coluna] = df[coluna].apply(converter_numero)
    else:
        df[coluna] = float("nan")

# Interpreta o placar (por exemplo, 60:50) apenas se a coluna estiver disponível.
if "GolsF/S" in df.columns:
    placar = df["GolsF/S"].astype("string").str.strip()
    gols = placar.str.extract(r"^\s*(\d+)\s*:\s*(\d+)\s*$")
    df["Gols_Feitos"] = pd.to_numeric(gols[0], errors="coerce")
    df["Gols_Sofridos"] = pd.to_numeric(gols[1], errors="coerce")
else:
    df["Gols_Feitos"] = float("nan")
    df["Gols_Sofridos"] = float("nan")

if df.empty:
    st.info(MENSAGEM_SEM_REGISTROS)
    st.stop()

# =========================
# FILTROS — UM ÚNICO CONJUNTO
# =========================
st.sidebar.header("Filtros")

clubes = sorted(df["_ClubeFiltro"].dropna().unique().tolist())
anos = sorted(df["_AnoFiltro"].dropna().unique().tolist(), key=ordenar_ano)

clubes_selecionados = st.sidebar.multiselect(
    "Selecione os clubes",
    options=clubes,
    default=clubes,
    key="elencos_clubes",
)
anos_selecionados = st.sidebar.multiselect(
    "Selecione as temporadas",
    options=anos,
    default=anos,
    key="elencos_anos",
)

df_filtrado = df.loc[
    df["_ClubeFiltro"].isin(clubes_selecionados)
    & df["_AnoFiltro"].isin(anos_selecionados)
].copy()

if df_filtrado.empty:
    mostrar_aviso_sem_registros()

# Ordem cronológica estável para tabelas e gráficos.
df_filtrado["_AnoOrdem"] = df_filtrado["_AnoExibicao"].apply(
    lambda valor: ordenar_ano(valor)[1]
)
df_filtrado = df_filtrado.sort_values(["_AnoOrdem", "_AnoExibicao"])

st.caption(
    f"Análise baseada em {len(df_filtrado)} registro(s), "
    f"{df_filtrado['_ClubeFiltro'].nunique()} clube(s) e "
    f"{df_filtrado['_AnoFiltro'].nunique()} temporada(s) selecionados."
)

# =========================
# INDICADORES
# =========================
st.subheader("📊 Resumo dos elencos")
col1, col2, col3, col4 = st.columns(4)
idade_media_geral = df_filtrado["Idade_Media"].mean()
estrangeiros_media = df_filtrado["Estrangeiros"].mean()
valor_medio = df_filtrado["Valor_total"].mean()

with col1:
    st.metric("Registros selecionados", f"{len(df_filtrado):,}".replace(",", "."))
with col2:
    st.metric("Idade média registrada", formatar_numero(idade_media_geral, 1))
with col3:
    st.metric("Média de estrangeiros por registro", formatar_numero(estrangeiros_media, 1))
with col4:
    st.metric("Valor médio do elenco", formatar_numero(valor_medio, 0))

if df_filtrado["Idade_Media"].notna().sum() == 0:
    st.warning("A coluna 'Idade_Media' não tem valores numéricos válidos para esta seleção.")
if df_filtrado["Estrangeiros"].notna().sum() == 0:
    st.warning("A coluna 'Estrangeiros' não tem valores numéricos válidos para esta seleção.")
if df_filtrado["Valor_total"].notna().sum() == 0:
    st.warning("A coluna 'Valor_total' não tem valores numéricos válidos para esta seleção.")

# =========================
# IDADE MÉDIA POR CLUBE
# =========================
st.subheader("🧑‍🤝‍🧑 Idade média por clube")
idade = df_filtrado.dropna(subset=["Idade_Media"]).groupby(
    "_ClubeExibicao", as_index=False
).agg(Idade_Media_Grupo=("Idade_Media", "mean"))

if not idade.empty:
    idade = idade.sort_values("Idade_Media_Grupo", ascending=True)
    grafico_idade = px.bar(
        idade,
        x="_ClubeExibicao",
        y="Idade_Media_Grupo",
        title="Idade média registrada por clube",
        labels={
            "_ClubeExibicao": "Clube",
            "Idade_Media_Grupo": "Idade média",
        },
        hover_data={"Idade_Media_Grupo": ":.1f"},
    )
    grafico_idade.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(grafico_idade, use_container_width=True)
    st.caption("Quando há mais de uma temporada selecionada, a barra mostra a média entre os registros do clube.")
else:
    st.info("Não há valores de idade média válidos para criar este gráfico.")

# =========================
# JOGADORES ESTRANGEIROS
# =========================
st.subheader("🌎 Jogadores estrangeiros")
estrangeiros = df_filtrado.dropna(subset=["Estrangeiros"]).groupby(
    "_ClubeExibicao", as_index=False
).agg(Estrangeiros_Medio=("Estrangeiros", "mean"))

if not estrangeiros.empty:
    estrangeiros = estrangeiros.sort_values("Estrangeiros_Medio", ascending=False)
    grafico_estrangeiros = px.bar(
        estrangeiros,
        x="_ClubeExibicao",
        y="Estrangeiros_Medio",
        title="Média de estrangeiros por registro do clube",
        labels={
            "_ClubeExibicao": "Clube",
            "Estrangeiros_Medio": "Média de estrangeiros",
        },
    )
    grafico_estrangeiros.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(grafico_estrangeiros, use_container_width=True)
else:
    st.info("Não há valores numéricos de estrangeiros para criar este gráfico.")

# =========================
# EVOLUÇÃO DO VALOR DO ELENCO
# =========================
st.subheader("💰 Evolução do valor dos elencos")
valores = df_filtrado.dropna(subset=["Valor_total"]).copy()
if not valores.empty:
    ordem_anos = sorted(valores["_AnoExibicao"].unique().tolist(), key=ordenar_ano)
    grafico_valores = px.line(
        valores,
        x="_AnoExibicao",
        y="Valor_total",
        color="_ClubeExibicao",
        markers=True,
        category_orders={"_AnoExibicao": ordem_anos},
        title="Valor total registrado por temporada",
        labels={
            "_AnoExibicao": "Temporada",
            "Valor_total": "Valor do elenco (unidade do CSV)",
            "_ClubeExibicao": "Clube",
        },
        hover_data=[col for col in ["Pos.", "Idade_Media", "Estrangeiros"] if col in valores.columns],
    )
    grafico_valores.update_yaxes(tickformat=",.0f")
    st.plotly_chart(grafico_valores, use_container_width=True)
else:
    st.info("Não há valores de elenco válidos para criar este gráfico.")

# =========================
# RELAÇÃO ENTRE IDADE E ESTRANGEIROS
# =========================
st.subheader("🔎 Idade média x jogadores estrangeiros")
relacao = df_filtrado.dropna(subset=["Idade_Media", "Estrangeiros"]).copy()
if not relacao.empty:
    grafico_relacao = px.scatter(
        relacao,
        x="Idade_Media",
        y="Estrangeiros",
        color="_ClubeExibicao",
        hover_data=["_AnoExibicao", "Valor_total"],
        title="Perfil dos elencos nas temporadas selecionadas",
        labels={
            "Idade_Media": "Idade média",
            "Estrangeiros": "Jogadores estrangeiros",
            "_ClubeExibicao": "Clube",
            "_AnoExibicao": "Temporada",
            "Valor_total": "Valor do elenco (unidade do CSV)",
        },
    )
    st.plotly_chart(grafico_relacao, use_container_width=True)
else:
    st.info("Não há registros com idade média e quantidade de estrangeiros válidas ao mesmo tempo.")

# =========================
# TABELA DETALHADA
# =========================
st.subheader("📋 Dados dos elencos selecionados")
colunas_tabela = [
    col for col in [
        "Ano", "Clubes", "Pos.", "Idade_Media", "Estrangeiros",
        "GolsF/S", "Valor_total",
    ] if col in df_filtrado.columns
]
tabela = df_filtrado[colunas_tabela].copy().rename(
    columns={
        "Ano": "Temporada",
        "Clubes": "Clube",
        "Pos.": "Posição",
        "Idade_Media": "Idade média",
        "Estrangeiros": "Estrangeiros",
        "GolsF/S": "Gols feitos : gols sofridos",
        "Valor_total": "Valor do elenco (unidade do CSV)",
    }
)
st.dataframe(tabela, use_container_width=True, hide_index=True)
