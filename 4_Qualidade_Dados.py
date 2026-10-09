import re

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Qualidade dos Dados",
    page_icon="🧹",
    layout="wide",
)

MENSAGEM_SEM_REGISTROS = (
    "Não há registros para essa seleção. O clube pode não ter disputado "
    "a Série A nessa temporada ou os dados podem estar ausentes da base."
)
SEM_CLUBE = "⟨Sem clube⟩"
SEM_TEMPORADA = "⟨Sem temporada⟩"


def carregar_dados():
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
    """Converte números inteiros/decimais e formatos localizados do CSV."""
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


def marcar_alerta(mascara, mensagem, mapa_alertas, indice):
    """Registra alertas por linha para a tabela de auditoria final."""
    mascara = mascara.fillna(False)
    for item_indice in indice[mascara.to_numpy()]:
        mapa_alertas.setdefault(item_indice, []).append(mensagem)


def adicionar_verificacao(lista, nome, quantidade, descricao):
    quantidade = int(quantidade)
    lista.append(
        {
            "Verificação": nome,
            "Registros/células afetados": quantidade,
            "Situação": "Atenção" if quantidade > 0 else "OK",
            "O que significa": descricao,
        }
    )


def mostrar_aviso_sem_registros():
    st.info(MENSAGEM_SEM_REGISTROS)
    st.stop()


st.title("🧹 Qualidade dos Dados")
st.write(
    "Confira valores ausentes, duplicatas, formatos incorretos e possíveis "
    "inconsistências no arquivo. Os filtros permitem investigar clubes e temporadas; "
    "a seleção inicial inclui também linhas sem clube ou temporada identificados."
)

# =========================
# LEITURA E PREPARAÇÃO
# =========================
df = carregar_dados()
colunas_csv = list(df.columns)
# Strings vazias e campos compostos apenas por espaços devem contar como ausentes.
df = df.replace(r"^\s*$", pd.NA, regex=True)

# Normalizações auxiliares são usadas nos filtros e nas regras de validação.
df["_AnoNormalizado"] = df["Ano"].apply(normalizar_ano).astype("string")
df["_ClubeNormalizado"] = df["Clubes"].apply(limpar_texto).astype("string")
df["_AnoFiltro"] = df["_AnoNormalizado"].fillna(SEM_TEMPORADA).astype(str)
df["_ClubeFiltro"] = df["_ClubeNormalizado"].fillna(SEM_CLUBE).astype(str)

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
    key="qualidade_clubes",
)
anos_selecionados = st.sidebar.multiselect(
    "Selecione as temporadas",
    options=anos,
    default=anos,
    key="qualidade_anos",
)

df_filtrado = df.loc[
    df["_ClubeFiltro"].isin(clubes_selecionados)
    & df["_AnoFiltro"].isin(anos_selecionados)
].copy()

if df_filtrado.empty:
    mostrar_aviso_sem_registros()

# Remove as colunas auxiliares para não contaminar as verificações de qualidade.
dados = df_filtrado[colunas_csv].copy()
# Regras trabalham com espaços em branco como dados ausentes, sem alterar o arquivo original.
dados = dados.replace(r"^\s*$", pd.NA, regex=True)

st.caption(
    f"Analisando {len(dados)} registro(s) de {len(colunas_csv)} coluna(s) "
    "após aplicar os filtros."
)

# =========================
# INDICADORES PRINCIPAIS
# =========================
total_linhas = len(dados)
total_colunas = len(dados.columns)
celulas_ausentes = int(dados.isna().sum().sum())
linhas_com_ausentes = int(dados.isna().any(axis=1).sum())
duplicatas_completas = int(dados.duplicated().sum())

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Registros analisados", f"{total_linhas:,}".replace(",", "."))
with col2:
    st.metric("Colunas analisadas", total_colunas)
with col3:
    st.metric("Células ausentes", f"{celulas_ausentes:,}".replace(",", "."))
with col4:
    st.metric("Linhas duplicadas extras", f"{duplicatas_completas:,}".replace(",", "."))

# =========================
# VALORES AUSENTES POR COLUNA
# =========================
st.subheader("1. Valores ausentes por coluna")
resumo_ausentes = pd.DataFrame(
    {
        "Coluna": dados.columns,
        "Valores ausentes": dados.isna().sum().values,
        "% ausente": (dados.isna().mean().values * 100).round(2),
    }
).sort_values(["Valores ausentes", "Coluna"], ascending=[False, True])

if celulas_ausentes > 0:
    grafico_ausentes = px.bar(
        resumo_ausentes,
        x="Coluna",
        y="% ausente",
        title="Percentual de valores ausentes por coluna",
        labels={"Coluna": "Coluna", "% ausente": "% ausente"},
        hover_data=["Valores ausentes"],
    )
    grafico_ausentes.update_layout(xaxis_tickangle=-35, yaxis_range=[0, 100])
    st.plotly_chart(grafico_ausentes, use_container_width=True)
else:
    st.success("Nenhum valor ausente foi encontrado nos registros selecionados.")

st.dataframe(resumo_ausentes, use_container_width=True, hide_index=True)

# =========================
# VERIFICAÇÕES E ALERTAS
# =================
checks = []
alertas_por_linha = {}

mascara_ausentes = dados.isna().any(axis=1)
marcar_alerta(
    mascara_ausentes,
    "Possui um ou mais campos ausentes",
    alertas_por_linha,
    dados.index,
)
adicionar_verificacao(
    checks,
    "Campos ausentes",
    linhas_com_ausentes,
    "Linhas com pelo menos um campo vazio ou ausente.",
)

mascara_duplicadas = dados.duplicated(keep=False)
marcar_alerta(
    mascara_duplicadas,
    "Linha completa duplicada",
    alertas_por_linha,
    dados.index,
)
adicionar_verificacao(
    checks,
    "Linhas completas duplicadas (extras)",
    duplicatas_completas,
    "Registros repetidos em todas as colunas; cada repetição extra conta uma vez.",
)

# Verifica se existe mais de uma linha para o mesmo clube e temporada.
if {"Ano", "Clubes"}.issubset(dados.columns):
    chaves = pd.DataFrame(index=dados.index)
    chaves["Ano"] = df_filtrado["_AnoNormalizado"]
    chaves["Clubes"] = df_filtrado["_ClubeNormalizado"]
    mascara_chave_valida = chaves.notna().all(axis=1)
    chaves_validas = chaves.loc[mascara_chave_valida]
    mascara_chave_duplicada_local = chaves_validas.duplicated(
        subset=["Ano", "Clubes"], keep=False
    )
    indices_chave_duplicada = chaves_validas.index[mascara_chave_duplicada_local]
    mascara_chave_duplicada = pd.Series(False, index=dados.index)
    mascara_chave_duplicada.loc[indices_chave_duplicada] = True
    extras_clube_temporada = int(
        chaves_validas.duplicated(subset=["Ano", "Clubes"]).sum()
    )
    marcar_alerta(
        mascara_chave_duplicada,
        "Clube e temporada repetidos",
        alertas_por_linha,
        dados.index,
    )
    adicionar_verificacao(
        checks,
        "Clube/temporada duplicados (extras)",
        extras_clube_temporada,
        "Mais de um registro para a mesma combinação de clube e temporada; confirme se é esperado.",
    )
else:
    adicionar_verificacao(
        checks,
        "Clube/temporada duplicados",
        0,
        "Não foi possível verificar porque faltam as colunas Ano ou Clubes.",
    )

# Ano: precisa conter um ano com quatro dígitos; ausências já são verificadas acima.
if "Ano" in dados.columns:
    ano_texto = dados["Ano"].astype("string").str.strip()
    mascara_ano_invalido = ano_texto.notna() & ~ano_texto.str.contains(r"\d{4}", regex=True, na=False)
    marcar_alerta(
        mascara_ano_invalido,
        "Formato de temporada não reconhecido",
        alertas_por_linha,
        dados.index,
    )
    adicionar_verificacao(
        checks,
        "Temporada sem ano de quatro dígitos",
        int(mascara_ano_invalido.sum()),
        "Valores preenchidos na coluna Ano que não contêm um ano com quatro dígitos.",
    )

# Placar: formato esperado, por exemplo 60:50.
if "GolsF/S" in dados.columns:
    placar = dados["GolsF/S"].astype("string").str.strip()
    mascara_placar_invalido = placar.notna() & ~placar.str.fullmatch(r"\d+\s*:\s*\d+", na=False)
    marcar_alerta(
        mascara_placar_invalido,
        "Formato de GolsF/S diferente de gols:gols",
        alertas_por_linha,
        dados.index,
    )
    adicionar_verificacao(
        checks,
        "Placar GolsF/S em formato inesperado",
        int(mascara_placar_invalido.sum()),
        "Valores preenchidos que não seguem o padrão 'gols feitos:gols sofridos', como 60:50.",
    )

# Verifica campos numéricos comuns se estiverem no arquivo.
colunas_numericas = [
    "Pos.", "V", "E", "D", "SG", "Pts", "Vitórias", "Empates",
    "Derrotas", "Idade_Media", "Estrangeiros", "Valor_total",
]
colunas_numericas_presentes = [col for col in colunas_numericas if col in dados.columns]
mascara_numerico_invalido = pd.Series(False, index=dados.index)
for coluna in colunas_numericas_presentes:
    original = dados[coluna]
    convertido = original.apply(converter_numero)
    mascara_coluna_invalida = original.notna() & convertido.isna()
    mascara_numerico_invalido = mascara_numerico_invalido | mascara_coluna_invalida
    marcar_alerta(
        mascara_coluna_invalida,
        f"Valor numérico inválido em {coluna}",
        alertas_por_linha,
        dados.index,
    )

adicionar_verificacao(
    checks,
    "Valores inválidos em colunas numéricas",
    int(mascara_numerico_invalido.sum()),
    "Linhas com ao menos um valor preenchido que não pôde ser convertido para número.",
)

# Valores que devem ser não negativos; saldo de gols (SG) fica de fora, pois pode ser negativo.
colunas_nao_negativas = [
    col for col in [
        "Pos.", "V", "E", "D", "Pts", "Vitórias", "Empates", "Derrotas",
        "Idade_Media", "Estrangeiros", "Valor_total",
    ] if col in dados.columns
]
mascara_negativos = pd.Series(False, index=dados.index)
for coluna in colunas_nao_negativas:
    convertido = dados[coluna].apply(converter_numero)
    limite = convertido.lt(0)
    if coluna in {"Pos.", "Idade_Media"}:
        limite = limite | convertido.eq(0)
    mascara_negativos = mascara_negativos | limite.fillna(False)
    marcar_alerta(
        limite.fillna(False),
        f"Valor negativo ou zero inesperado em {coluna}",
        alertas_por_linha,
        dados.index,
    )

adicionar_verificacao(
    checks,
    "Valores negativos/zero inesperados",
    int(mascara_negativos.sum()),
    "Posição e idade média devem ser positivas; vitórias, empates, derrotas, pontos, estrangeiros e valor não devem ser negativos.",
)

# Idade média: alerta adicional para um valor extremo, sem presumir que todo valor fora do padrão seja erro.
if "Idade_Media" in dados.columns:
    idade = dados["Idade_Media"].apply(converter_numero)
    mascara_idade_extrema = idade.notna() & ((idade < 15) | (idade > 60))
    marcar_alerta(
        mascara_idade_extrema,
        "Idade média fora da faixa de conferência (15–60)",
        alertas_por_linha,
        dados.index,
    )
    adicionar_verificacao(
        checks,
        "Idade média fora de 15–60",
        int(mascara_idade_extrema.sum()),
        "Faixa de triagem para revisão manual, não uma prova automática de erro.",
    )

# =========================
# RESUMO DAS VERIFICAÇÕES
# =========================
st.subheader("2. Resultado das verificações")
tabela_checks = pd.DataFrame(checks)
st.dataframe(
    tabela_checks,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Verificação": st.column_config.TextColumn("Verificação", width="medium"),
        "Registros/células afetados": st.column_config.NumberColumn(
            "Registros/células afetados", format="%d"
        ),
        "Situação": st.column_config.TextColumn("Situação", width="small"),
        "O que significa": st.column_config.TextColumn("O que significa", width="large"),
    },
)

quantidade_alertas = sum(len(itens) for itens in alertas_por_linha.values())
if all(check["Situação"] == "OK" for check in checks):
    st.success("As verificações executadas não encontraram problemas nesses critérios.")
else:
    st.warning(
        "Há pontos que merecem conferência. Os alertas ajudam a localizar possíveis problemas, "
        "mas alguns casos podem ser válidos dependendo da origem dos dados."
    )

# =========================
# REGISTROS QUE PRECISAM DE CONFERÊNCIA
# =========================
st.subheader("3. Registros que precisam de conferência")
if alertas_por_linha:
    linhas_alerta = []
    colunas_contexto = [
        col for col in ["Ano", "Clubes", "Pos.", "GolsF/S", "Idade_Media", "Estrangeiros", "Valor_total"]
        if col in dados.columns
    ]
    for indice, mensagens in alertas_por_linha.items():
        linha = dados.loc[indice, colunas_contexto].to_dict()
        linha["Alertas"] = "; ".join(dict.fromkeys(mensagens))
        linhas_alerta.append(linha)

    tabela_alertas = pd.DataFrame(linhas_alerta)
    st.dataframe(tabela_alertas, use_container_width=True, hide_index=True)
    st.caption(
        "Esta lista reúne linhas com pelo menos um alerta. Verifique a fonte antes de alterar o CSV; "
        "um alerta não significa necessariamente que o registro esteja errado."
    )
else:
    st.success("Nenhum registro precisou de conferência nas regras aplicadas.")

# =========================
# DADOS FILTRADOS
# =========================
with st.expander("Ver os registros completos selecionados"):
    st.dataframe(dados, use_container_width=True, hide_index=True)

st.caption(
    "Esta página apenas identifica possíveis problemas. Ela não altera nem sobrescreve o CSV original."
)
