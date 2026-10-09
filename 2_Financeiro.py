import re
import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================

st.set_page_config(
    page_title="Análise Financeira",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Análise Financeira")
st.write(
    "Compare o valor dos elencos e descubra como eles "
    "evoluíram ao longo das temporadas."
)

# =========================
# CARREGAMENTO DOS DADOS
# =========================

df = pd.read_csv("Tabela_Clubes.csv")

colunas_necessarias = ["Ano", "Clubes", "Valor_total", "Pos."]
colunas_faltantes = [
    coluna for coluna in colunas_necessarias
    if coluna not in df.columns
]

if colunas_faltantes:
    st.error(
        "Colunas ausentes no CSV: "
        + ", ".join(colunas_faltantes)
    )
    st.stop()

# Padronizar os nomes dos clubes e das temporadas
df["Clubes"] = df["Clubes"].astype("string").str.strip()
df["Ano"] = df["Ano"].astype("string").str.strip()

# Remover registros sem clube ou temporada
df = df.dropna(subset=["Clubes", "Ano"]).copy()
df = df[
    df["Clubes"].ne("") & df["Ano"].ne("")
].copy()

# =========================
# TRATAMENTO DOS VALORES
# =========================

def converter_valor(valor):
    if pd.isna(valor):
        return float("nan")

    texto = str(valor).strip()

    if not texto:
        return float("nan")

    texto = (
        texto.replace("R$", "")
        .replace("$", "")
        .replace("€", "")
        .replace(" ", "")
    )

    # Manter somente números e separadores
    texto = re.sub(r"[^\d,.\-]", "", texto)

    if not texto:
        return float("nan")

    if "," in texto:
        # Exemplo: 1.234,56 -> 1234.56
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", texto):
        # Exemplo: 1.234.567 -> 1234567
        texto = texto.replace(".", "")

    return pd.to_numeric(texto, errors="coerce")


df["Valor_total"] = df["Valor_total"].apply(converter_valor)
df["Pos."] = pd.to_numeric(df["Pos."], errors="coerce")

# Criar uma ordem cronológica para as temporadas
df["Ano_Ordem"] = pd.to_numeric(
    df["Ano"].str.extract(r"(\d{4})", expand=False),
    errors="coerce"
)


# =========================
# FILTROS
# =========================

st.sidebar.header("Filtros")

clubes = sorted(df["Clubes"].dropna().unique().tolist())


def ordenar_ano(ano):
    encontrado = re.search(r"\d{4}", str(ano))

    if encontrado:
        return (int(encontrado.group()), str(ano))

    return (9999, str(ano))


anos = sorted(
    df["Ano"].dropna().unique().tolist(),
    key=ordenar_ano
)

clube_selecionado = st.sidebar.selectbox(
    "Clube",
    options=["Todos os clubes"] + clubes
)

temporada_selecionada = st.sidebar.selectbox(
    "Temporada",
    options=["Todas as temporadas"] + anos
)

# Aplicar os filtros
df_filtrado = df.copy()

if clube_selecionado != "Todos os clubes":
    df_filtrado = df_filtrado[
        df_filtrado["Clubes"] == clube_selecionado
    ]

if temporada_selecionada != "Todas as temporadas":
    df_filtrado = df_filtrado[
        df_filtrado["Ano"] == temporada_selecionada
    ]

if df_filtrado.empty:
    st.info(
        "Não há registros para essa seleção. "
        "O clube pode não ter disputado a Série A nessa temporada "
        "ou os dados podem estar ausentes da base."
    )
    st.stop()
# Ordenar as temporadas
df_filtrado = df_filtrado.sort_values("Ano")

# A partir daqui, usar apenas valores financeiros válidos
df_valido = df_filtrado.dropna(
    subset=["Valor_total"]
).copy()

if df_valido.empty:
    st.warning(
        "Os filtros encontraram registros, mas os valores financeiros "
        "não foram reconhecidos como números. Confira a coluna Valor_total."
    )

    st.dataframe(
        df_filtrado[["Ano", "Clubes", "Valor_total"]],
        use_container_width=True,
        hide_index=True
    )

    st.stop()

# =========================
# FORMATAÇÃO MONETÁRIA
# =========================

def formatar_reais(valor):
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

# =========================
# INDICADORES FINANCEIROS
# =========================

st.subheader("📊 Resumo financeiro")

col1, col2, col3 = st.columns(3)

valor_medio = df_valido["Valor_total"].mean()

maior_registro = df_valido.loc[
    df_valido["Valor_total"].idxmax()
]

menor_registro = df_valido.loc[
    df_valido["Valor_total"].idxmin()
]

with col1:
    st.metric(
        "Valor médio dos elencos",
        formatar_reais(valor_medio)
    )

with col2:
    st.metric(
        "Maior valor registrado",
        formatar_reais(maior_registro["Valor_total"])
    )
    st.caption(
        f'{maior_registro["Clubes"]} — {maior_registro["Ano"]}'
    )

with col3:
    st.metric(
        "Menor valor registrado",
        formatar_reais(menor_registro["Valor_total"])
    )
    st.caption(
        f'{menor_registro["Clubes"]} — {menor_registro["Ano"]}'
    )

st.caption(
    "Os indicadores consideram os clubes e as temporadas selecionados."
)

# =========================
# EVOLUÇÃO DOS VALORES
# =========================

st.subheader("📈 Evolução do valor dos elencos")

ordem_temporadas = sorted(
    df_valido["Ano"].unique().tolist(),
    key=ordenar_ano
)

grafico_evolucao = px.line(
    df_valido,
    x="Ano",
    y="Valor_total",
    color="Clubes",
    markers=True,
    category_orders={"Ano": ordem_temporadas},
    title="Valor dos elencos ao longo das temporadas",
    labels={
        "Ano": "Temporada",
        "Valor_total": "Valor do elenco (R$)",
        "Clubes": "Clube"
    }
)

grafico_evolucao.update_yaxes(
    tickprefix="R$ ",
    tickformat=",.0f"
)

st.plotly_chart(
    grafico_evolucao,
    use_container_width=True
)

# =========================
# COMPARAÇÃO ENTRE CLUBES
# =========================

st.subheader("🏆 Comparação entre clubes")

ultima_temporada = ordem_temporadas[-1]

df_comparacao = df_valido[
    df_valido["Ano"] == ultima_temporada
].sort_values("Valor_total", ascending=True)

grafico_comparacao = px.bar(
    df_comparacao,
    x="Valor_total",
    y="Clubes",
    orientation="h",
    title=f"Valor dos elencos — {ultima_temporada}",
    labels={
        "Valor_total": "Valor do elenco (R$)",
        "Clubes": "Clube"
    }
)

grafico_comparacao.update_xaxes(
    tickprefix="R$ ",
    tickformat=",.0f"
)

st.plotly_chart(
    grafico_comparacao,
    use_container_width=True
)

# =========================
# VALOR DO ELENCO X POSIÇÃO
# =========================

st.subheader("🔎 Valor do elenco x classificação")

dados_relacao = df_valido.dropna(
    subset=["Valor_total", "Pos."]
)

if not dados_relacao.empty:
    grafico_relacao = px.scatter(
        dados_relacao,
        x="Valor_total",
        y="Pos.",
        color="Clubes",
        hover_data=["Ano"],
        title="Valor financeiro e posição na liga",
        labels={
            "Valor_total": "Valor do elenco (R$)",
            "Pos.": "Posição na tabela",
            "Clubes": "Clube",
            "Ano": "Temporada"
        }
    )

    grafico_relacao.update_yaxes(
        autorange="reversed"
    )

    grafico_relacao.update_xaxes(
        tickprefix="R$ ",
        tickformat=",.0f"
    )

    st.plotly_chart(
        grafico_relacao,
        use_container_width=True
    )

    st.caption(
        "Uma relação entre valor e classificação não prova que um "
        "elenco mais caro causa melhores resultados esportivos."
    )
else:
    st.info(
        "Não há dados suficientes para comparar valor e classificação."
    )

# =========================
# VARIAÇÃO PERCENTUAL
# =========================

st.subheader("📊 Variação do valor entre temporadas")

evolucao = []

df_ordenado = df_valido.sort_values(
    ["Ano_Ordem", "Ano"]
)

for clube, dados in df_ordenado.groupby("Clubes"):
    dados = dados.drop_duplicates(
        subset=["Ano"],
        keep="last"
    ).sort_values(["Ano_Ordem", "Ano"])

    if len(dados) < 2:
        continue

    primeiro = dados.iloc[0]
    ultimo = dados.iloc[-1]

    valor_inicial = primeiro["Valor_total"]
    valor_final = ultimo["Valor_total"]

    if valor_inicial == 0:
        variacao = None
    else:
        variacao = (
            (valor_final - valor_inicial)
            / abs(valor_inicial)
        ) * 100

    evolucao.append({
        "Clube": clube,
        "Temporada inicial": primeiro["Ano"],
        "Valor inicial": formatar_reais(valor_inicial),
        "Temporada final": ultimo["Ano"],
        "Valor final": formatar_reais(valor_final),
        "Variação (%)": (
            f"{variacao:+.2f}%"
            if variacao is not None
            else "Indisponível"
        )
    })

if evolucao:
    st.dataframe(
        pd.DataFrame(evolucao),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info(
        "Selecione pelo menos duas temporadas com valores válidos "
        "para comparar a evolução."
    )

# =========================
# HISTÓRICO FINANCEIRO
# =========================

st.subheader("📋 Histórico dos valores")

historico = df_filtrado.sort_values(
    ["Ano_Ordem", "Valor_total"],
    ascending=[True, False],
    na_position="last"
)[["Ano", "Clubes", "Valor_total", "Pos."]].rename(
    columns={
        "Ano": "Temporada",
        "Clubes": "Clube",
        "Valor_total": "Valor do elenco (R$)",
        "Pos.": "Posição"
    }
)

st.dataframe(
    historico,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Valor do elenco (R$)": st.column_config.NumberColumn(
            "Valor do elenco (R$)",
            format="R$ %.2f"
        )
    }
)