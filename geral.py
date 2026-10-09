import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(layout='wide')

# Leitura e tratamento inicial dos dados
df = pd.read_csv('Tabela_Clubes.csv')

# Conversões e limpezas necessárias para evitar erros de tipo (string -> float/int)
df['Gols_Feitos'] = df['GolsF/S'].astype(str).apply(lambda x: int(x.split(':')[0]) if ':' in x else 0)
df['Gols_Sofridos'] = df['GolsF/S'].astype(str).apply(lambda x: int(x.split(':')[1]) if ':' in x else 0)

df['Idade_Media'] = pd.to_numeric(
    df['Idade_Media'].astype(str).str.replace(',', '.', regex=False), 
    errors='coerce'
)

# Limpeza do Valor_total (removendo símbolos de moeda e ajustando pontos/vírgulas se houver)
df['Valor_total'] = pd.to_numeric(
    df['Valor_total'].astype(str)
    .str.replace('R$', '', regex=False)
    .str.replace('.', '', regex=False)
    .str.replace(',', '.', regex=False)
    .str.strip(),
    errors='coerce'
)

# ============================== SIDEBAR

# ============================== SIDEBAR

lista_anos = sorted(df['Ano'].dropna().unique().tolist())

lista_clubes = sorted(df['Clubes'].dropna().unique().tolist())

filtro_anos = st.sidebar.multiselect(
    'Selecione as temporadas',
    options=lista_anos,
    default=lista_anos
)

filtro_clubes = st.sidebar.multiselect(
    'Selecione os clubes',
    options=lista_clubes,
    default=lista_clubes
)
# ================================= BODY
# Filtro otimizado com .isin()
df = df[
    df['Ano'].isin(filtro_anos)
    & df['Clubes'].isin(filtro_clubes)
]
if df.empty:
    st.info(
        "Não há registros para essa seleção. "
        "O clube pode não ter disputado a Série A nessa temporada "
        "ou os dados podem estar ausentes da base."
    )
    st.stop()

with st.container():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.metric('Quantidade de estrangeiros', int(df['Estrangeiros'].sum()))

    with col2:
        with st.container(border=True):
            idade_media = df['Idade_Media'].mean()
            # Tratamento caso a média retorne NaN
            val_idade = f"{idade_media:.0f}" if pd.notnull(idade_media) else "0"
            st.metric('Idade média dos jogadores', val_idade)
    
    with col3:
        with st.container(border=True):
            valor_medio = df['Valor_total'].mean()
            val_medio_str = f"R$ {valor_medio:,.0f}" if pd.notnull(valor_medio) else "R$ 0"
            st.metric('Valor médio dos times', val_medio_str)

with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            podio = df[df['Pos.'] <= 5][['Ano', 'Pos.', 'Clubes']].sort_values(['Ano', 'Pos.'])
            st.table(podio)

    with col2:
        with st.container():
            g1 = px.bar(df, x='Clubes', y='Gols_Feitos', title='Total de Gols Feitos')
            st.plotly_chart(g1, use_container_width=True)
            
            g2 = px.line(df, x='Ano', y='Valor_total', color='Clubes', markers=True, title='Valor Total dos times através dos anos')
            st.plotly_chart(g2, use_container_width=True)