import json
import time
<<<<<<< HEAD
=======
import unicodedata
>>>>>>> 343162d (feat: change sheet format & compile desk and mobile analysis)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google import genai

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        text-align: center;
        display: flex;
        justify-content: center;
    }
    [data-testid="stMetricLabel"] {
        text-align: center;
        display: flex;
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Senha de Acesso",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Senha de Acesso",
            type="password",
            on_change=password_entered,
            key="password",
        )
        st.error("😕 Senha incorreta")
        return False
    else:
        return True


USE_MOCK_GEMINI = False


def _parse_keys(raw: str) -> list[str]:
    return [k.strip() for k in raw.split(",") if k.strip()]


if "GEMINI_API_KEY" in st.secrets:
    GEMINI_KEYS = _parse_keys(st.secrets["GEMINI_API_KEY"])
else:
    with st.sidebar:
        st.warning("Chave API não encontrada nos Secrets.")
        raw = st.text_input("Insira sua(s) Gemini API Key(s):", type="password")
        GEMINI_KEYS = _parse_keys(raw)

if not GEMINI_KEYS:
    st.error("Por favor, configure a API Key para continuar.")
    st.stop()
if "gemini_key_idx" not in st.session_state:
    st.session_state.gemini_key_idx = 0


MODEL_NAME = "gemini-2.5-flash-lite"

CATEGORIAS = [
    "Entrega",
    "Frete",
    "Produto",
    "Pagamento",
    "Atendimento",
    "Site / Performance",
    "Navegação / UX",
    "Outros",
]

PROMPT_PARCIAL = """
Você é uma assistente especializada em análise de NPS da marca Track&Field.

Você receberá uma lista de comentários no formato:
nota-comentário (Grupo NPS)

Analise os comentários e retorne exatamente neste formato:

Categorias Mais Citadas:
- Entrega: percentual aproximado e exemplo curto
- Frete: percentual aproximado e exemplo curto
- Produto: percentual aproximado e exemplo curto
- Pagamento: percentual aproximado e exemplo curto
- Atendimento: percentual aproximado e exemplo curto
- Navegação / UX: percentual aproximado e exemplo curto
- Outros: percentual aproximado e exemplo curto

Por Grupo NPS:
- Detratores (0–6): principais reclamações e tom emocional
- Neutros (7–8): pontos de atenção e expectativas
- Promotores (9–10): principais elogios

Sentimento Geral:
- positivo, neutro ou negativo, com breve justificativa

Regras:
- Sempre preencher todos os grupos NPS
- Usar percentuais aproximados baseados na frequência dos temas
- Não usar markdown
- Não usar emojis
- Texto simples
- Português brasileiro
"""

PROMPT_FINAL = """
Você receberá resumos de análises NPS separadas por canal.

Consolide tudo em um único relatório executivo, exatamente neste formato:

Resumo da Análise NPS:
----------------------
Principais Gargalos:
- ...

Por Grupo NPS:
- Detratores (0–6): ...
- Neutros (7–8): ...
- Promotores (9–10): ...

Desktop x Mobile:
- Mobile: ...
- Desktop: ...

Sentimento Geral:
- percentual aproximado positivo, neutro e negativo, com interpretação

Regras:
- Nunca usar N/A
- Mesmo com pouco volume, sempre interpretar
- Não usar markdown, emojis ou símbolos especiais
- Texto simples
- Português brasileiro
"""

PROMPT_TENDENCIA = """
Você é uma assistente especializada em análise de NPS da marca Track&Field.

Você receberá comentários de clientes de um único mês.

Classifique cada tema mencionado nas categorias abaixo e estime a porcentagem de comentários que cita cada uma.
<<<<<<< HEAD
As porcentagens NÃO precisam somar 100% — um comentário pode mencionar mais de um tema.
=======
As porcentagens NÃO precisam somar 100% - um comentário pode mencionar mais de um tema.
>>>>>>> 343162d (feat: change sheet format & compile desk and mobile analysis)

Categorias (use exatamente estes nomes):
- Entrega
- Frete
- Produto
- Pagamento
- Atendimento
- Site / Performance
- Navegação / UX
- Outros

IMPORTANTE: "Site / Performance" deve capturar qualquer menção a lentidão, travamento, instabilidade, erro, falha técnica ou demora no carregamento do site.

Retorne SOMENTE um JSON válido, sem texto adicional, sem markdown, sem blocos de código, exatamente neste formato:
{
  "Entrega": 12,
  "Frete": 8,
  "Produto": 35,
  "Pagamento": 5,
  "Atendimento": 10,
  "Site / Performance": 15,
  "Navegação / UX": 10,
  "Outros": 20
}
"""

<<<<<<< HEAD
=======
PROMPT_OUTROS = """
Você é uma assistente especializada em análise de pesquisas da marca Track&Field.

Você receberá uma lista de respostas abertas ("Outros") que clientes escreveram em uma pergunta
de múltipla escolha, para a pergunta abaixo:

PERGUNTA: {pergunta}

Resuma os principais temas citados nessas respostas.

Retorne exatamente neste formato:

Principais temas citados:
- tema 1: percentual aproximado e exemplo curto
- tema 2: percentual aproximado e exemplo curto
- tema 3: percentual aproximado e exemplo curto
(liste quantos temas fizerem sentido, no máximo 6)

Observações:
- eventuais respostas que pareçam lixo de teste (ex: "teste", "123", respostas sem sentido) devem ser
  citadas à parte, sem entrar no percentual dos temas reais

Regras:
- Não usar markdown
- Não usar emojis
- Texto simples
- Português brasileiro
"""

>>>>>>> 343162d (feat: change sheet format & compile desk and mobile analysis)

def _col(df, keyword):
    """Retorna o índice da primeira coluna cujo nome contém o keyword (case-insensitive)."""
    for i, col in enumerate(df.columns):
        if keyword.lower() in str(col).lower():
            return i
    raise ValueError(
        f"Coluna com '{keyword}' não encontrada. Colunas disponíveis: {list(df.columns)}"
    )


def grupo_nps(nota):
    if nota >= 9:
        return "Promotores"
    if nota >= 7:
        return "Neutros"
    return "Detratores"


def carregar_df_bruto(file):
    return pd.read_excel(file, header=14)


def carregar_comentarios(df):
    col_nota = _col(df, "experiência geral")
    col_comentario = _col(df, "Deixe seu comentário")

    comentarios = []
    for _, row in df.iterrows():
        try:
            nota = int(pd.to_numeric(row.iloc[col_nota], errors="coerce"))
        except:
            continue
        comentario = str(row.iloc[col_comentario]).strip()
        if not comentario or comentario.lower() in (
            "nan",
            "sem comentários.",
            "sem comentários",
        ):
            continue
        grupo = grupo_nps(nota)
        comentarios.append(f"{nota}-{comentario} ({grupo})")
    return comentarios


def carregar_comentarios_por_mes(df):
    df = df.copy()
    col_nota = _col(df, "experiência geral")
    col_comentario = _col(df, "Deixe seu comentário")
    df["_data"] = pd.to_datetime(df.iloc[:, 0], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["_data"])
    df["_periodo"] = df["_data"].dt.to_period("M")

    resultado = {}
    for periodo, grupo in df.groupby("_periodo"):
        comentarios = []
        for _, row in grupo.iterrows():
            try:
                nota = int(pd.to_numeric(row.iloc[col_nota], errors="coerce"))  # col 4
            except:
                continue
            comentario = str(row.iloc[col_comentario]).strip()  # col 6
            if not comentario or comentario.lower() in (
                "nan",
                "sem comentários.",
                "sem comentários",
            ):
                continue
            grupo_label = grupo_nps(nota)
            comentarios.append(f"{nota}-{comentario} ({grupo_label})")
        if comentarios:
            resultado[str(periodo)] = comentarios

    return dict(sorted(resultado.items()))


def calcular_notas(df):
    col_nota = _col(df, "experiência geral")
    notas = pd.to_numeric(df.iloc[:, col_nota], errors="coerce").dropna().astype(int)
    return notas.value_counts().reindex(range(0, 11), fill_value=0).sort_index()


def calcular_facilidade(df):
    col_facilidade = _col(df, "fácil foi navegar")
    facilidade = (
        df.iloc[:, col_facilidade].astype(str).replace({"nan": "(não respondeu)"})
    )
    ordem = [
        "Muito fácil",
        "Fácil",
        "Neutro",
        "Difícil",
        "Muito difícil",
        "(não respondeu)",
    ]
    return facilidade.value_counts().reindex(ordem, fill_value=0)


def calcular_nps_por_notas(series_notas):
    total = series_notas.sum()
    if total == 0:
        return 0
    promotores = series_notas.loc[9:10].sum()
    detratores = series_notas.loc[0:6].sum()
    return int(((promotores - detratores) / total) * 100)


def _next_client():
    """Retorna um client usando a chave atual e avança o índice."""
    idx = st.session_state.gemini_key_idx % len(GEMINI_KEYS)
    return genai.Client(api_key=GEMINI_KEYS[idx]), idx


def chamar_gemini(_client_ignorado, prompt, conteudo):
    if USE_MOCK_GEMINI:
        return """...""".strip()
    erros = []
    for _ in range(len(GEMINI_KEYS) * 2):  # até 2 voltas pelo pool
        client, idx = _next_client()
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=f"{prompt}\n\n{conteudo}",
            )
            st.session_state.gemini_key_idx = (idx + 1) % len(GEMINI_KEYS)
            return resp.text
        except Exception as e:
            erros.append(f"chave {idx + 1}: {e}")
            st.session_state.gemini_key_idx = (idx + 1) % len(GEMINI_KEYS)
            time.sleep(1)
    st.error(f"Todas as chaves falharam: {'; '.join(erros)}")
    raise RuntimeError("Falha em todas as chaves Gemini")


def chamar_gemini_tendencia(_client_ignorado, comentarios):
    if USE_MOCK_GEMINI:
        return {cat: 10 for cat in CATEGORIAS}
    conteudo = "\n".join(comentarios)
    erros = []

    for _ in range(len(GEMINI_KEYS) * 2):
        client, idx = _next_client()
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=f"{PROMPT_TENDENCIA}\n\n{conteudo}",
            )
            st.session_state.gemini_key_idx = (idx + 1) % len(GEMINI_KEYS)
            raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            erros.append(f"chave {idx + 1}: {e}")
            st.session_state.gemini_key_idx = (idx + 1) % len(GEMINI_KEYS)
            time.sleep(1)

    st.warning(f"Todas as chaves falharam: {'; '.join(erros)}")
    return {cat: 0 for cat in CATEGORIAS}


def gerar_grafico_tendencia(dados_tendencia, titulo):
    """
    dados_tendencia: dict {periodo_str: {categoria: pct}}
    """
    periodos = list(dados_tendencia.keys())
    fig = go.Figure()

    # Destaque visual para Site / Performance
    cores = {
        "Site / Performance": "#e63946",
        "Entrega": "#457b9d",
        "Frete": "#2a9d8f",
        "Produto": "#e9c46a",
        "Pagamento": "#f4a261",
        "Atendimento": "#264653",
        "Navegação / UX": "#a8dadc",
        "Outros": "#adb5bd",
    }

    for cat in CATEGORIAS:
        valores = [dados_tendencia[p].get(cat, 0) for p in periodos]
        largura = 3 if cat == "Site / Performance" else 1.5
        dash = "solid" if cat == "Site / Performance" else "dot"
        fig.add_trace(
            go.Scatter(
                x=periodos,
                y=valores,
                mode="lines+markers",
                name=cat,
                line=dict(color=cores.get(cat, "#888"), width=largura, dash=dash),
            )
        )

    fig.update_layout(
        title=titulo,
        xaxis_title="Mês",
        yaxis_title="% dos comentários",
        yaxis=dict(range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=-0.4),
        height=480,
        margin=dict(b=120),
    )
    return fig


<<<<<<< HEAD
# ── Session state ─────────────────────────────────────────────────────────────
=======
# ══════════════════════════════════════════════════════════════════════════
# ── Novo módulo: campanhas Insider (Exit Intent PDP / Carrinho, Progressive
#    Profile). A lógica de NPS acima permanece intacta e não é usada aqui.
# ══════════════════════════════════════════════════════════════════════════

# Cada pergunta é identificada por um trecho único (match) que existe na
# coluna correspondente tanto na planilha Desktop quanto na Mobile.
# "opcoes": None indica que a lista oficial de opções ainda não foi
# confirmada - nesse caso todas as respostas são exibidas como distribuição
# bruta, sem separar "oficial" x "Outros".
CAMPANHAS_CONFIG = {
    "PDP": {
        "label": "Intenção de saída - PDP",
        "perguntas": [
            {
                "chave": "motivo_saida",
                "titulo": "Antes de sair, o que faltou para adicionar este produto à sacola?",
                "match": "adicionar este produto à sacola",
                "opcoes": [
                    "Ainda estou pesquisando",
                    "Faltaram informações sobre o produto",
                    "Senti falta de informações sobre a entrega",
                    "Não encontrei meu tamanho ou cor",
                    "Fiquei em dúvida sobre qual tamanho escolher",
                    "Estou com problemas técnicos (carregamento lento, travamento…)",
                ],
            },
            {
                "chave": "info_produto",
                "titulo": "Quais informações sobre o produto você sentiu falta?",
                "match": "quais informações você sentiu falta",
                "opcoes": [
                    "Mais fotos mostrando os detalhes da peça (textura, costura e acabamento)",
                    "Um vídeo mostrando o produto em uso e o caimento no corpo",
                    "Mais informações sobre o produto (tecido, tecnologias, benefícios ou modelagem)",
                    "Um guia de medidas mais completo para escolher o tamanho ideal",
                ],
            },
            {
                "chave": "info_entrega",
                "titulo": "Quais informações sobre a entrega você sentiu falta?",
                "match": "informações sobre a entrega você sentiu falta",
                "opcoes": [
                    "Prazo estimado de entrega",
                    "Valor do frete",
                    "Disponibilidade de entrega para o meu CEP",
                    "Opções de entrega disponíveis",
                ],
            },
        ],
    },
    "CARRINHO": {
        "label": "Intenção de saída - Carrinho",
        "perguntas": [
            {
                "chave": "motivo_saida",
                "titulo": "Antes de você ir, o que fez você parar por aqui?",
                "match": "o que fez você parar por aqui",
                "opcoes": [
                    "Vou finalizar depois",
                    "O prazo de entrega não me agradou",
                    "Quero pesquisar outras opções antes de decidir",
                    "Senti falta de mais opções de pagamento e parcelamento",
                    "Estou com problemas técnicos (carregamento lento, travamento…)",
                ],
            },
        ],
    },
    "PROGRESSIVE": {
        "label": "Progressive Profile",
        "perguntas": [
            {
                "chave": "rotina",
                "titulo": "Qual movimento faz parte da sua rotina hoje?",
                "match": "qual movimento faz parte da sua rotina hoje",
                "opcoes": [
                    "Corrida",
                    "Treino (musculação, funcional e cross training)",
                    "Yoga, pilates e alongamento",
                    "Tênis e beach tennis",
                    "Ciclismo",
                    "Natação",
                    "Triathlon",
                    "Lifestyle (dia a dia)",
                ],
            },
            {
                "chave": "busca_site",
                "titulo": "O que você costuma procurar quando entra no site T&F?",
                "match": "o que você costuma procurar quando entra no site",
                "opcoes": [
                    "Novidades e lançamentos",
                    "Presentes para alguém especial",
                    "Produtos para minha prática esportiva",
                    "Looks para o dia a dia",
                    "Acessórios e calçados",
                    "Seleções com valores especiais",
                ],
            },
            {
                "chave": "produtos_explorar",
                "titulo": "Quais produtos você mais gosta de explorar?",
                "match": "quais produtos você mais gosta de explorar",
                "opcoes": [
                    "Casacos e jaquetas",
                    "Camisetas e regatas",
                    "Leggings",
                    "Calças",
                    "Tops",
                    "Shorts e bermudas",
                    "Macacões",
                    "Beachwear",
                    "Bolsas, malas e mochilas",
                    "Bonés e viseiras",
                    "Garrafas",
                ],
            },
            # Opções oficiais ainda não confirmadas com o time - ao receber a
            # lista, basta preencher "opcoes" igual às perguntas acima.
            {
                "chave": "performance",
                "titulo": "O que você busca hoje para elevar a sua performance ou rotina?",
                "match": "para elevar a sua performance ou rotina",
                "opcoes": None,
            },
            {
                "chave": "inegociavel",
                "titulo": "Ao escolher um produto esportivo, o que é inegociável para você?",
                "match": "absolutamente inegociável para você",
                "opcoes": None,
            },
            {
                "chave": "motivacao",
                "titulo": "Existe alguma motivação específica para a sua busca hoje?",
                "match": "motivação específica para a sua busca hoje",
                "opcoes": None,
            },
            {
                "chave": "exclusividade",
                "titulo": "Pensando em uma experiência de compra exclusiva, o que mais valoriza?",
                "match": "experiência de compra exclusiva no site",
                "opcoes": None,
            },
        ],
    },
}


def _normaliza(texto):
    texto = str(texto).strip().lower().rstrip(".!?")
    return unicodedata.normalize("NFKD", texto)


def carregar_datas(df):
    return pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")


def filtrar_por_periodo(df, data_ini, data_fim):
    datas = carregar_datas(df)
    mask = (datas.dt.date >= data_ini) & (datas.dt.date <= data_fim)
    return df[mask]


def classificar_pergunta(df, pergunta_cfg):
    """
    Retorna (contagem: dict[str, int], outros: list[str]).
    Se a pergunta não existir na planilha (coluna não encontrada), retorna (None, None).
    """
    try:
        col = _col(df, pergunta_cfg["match"])
    except ValueError:
        return None, None

    respostas = df.iloc[:, col].dropna().astype(str).str.strip()
    respostas = respostas[~respostas.str.lower().isin(["nan", ""])]

    opcoes = pergunta_cfg["opcoes"]
    if not opcoes:
        # Sem lista oficial ainda: mostra distribuição bruta das respostas
        return respostas.value_counts().to_dict(), []

    mapa_norm = {_normaliza(o): o for o in opcoes}
    contagem = {o: 0 for o in opcoes}
    outros = []
    for resp in respostas:
        norm = _normaliza(resp)
        if norm in mapa_norm:
            contagem[mapa_norm[norm]] += 1
        else:
            outros.append(resp)
    return contagem, outros


def gerar_grafico_distribuicao(contagem_mobile, contagem_desktop, titulo):
    """
    contagem_mobile / contagem_desktop: dict[str, int] ou None (canal ausente)
    Mostra % de respondentes de cada canal que escolheu cada opção.
    """
    opcoes = []
    if contagem_mobile:
        opcoes = list(contagem_mobile.keys())
    elif contagem_desktop:
        opcoes = list(contagem_desktop.keys())

    fig = go.Figure()

    if contagem_mobile:
        total_m = sum(contagem_mobile.values()) or 1
        fig.add_trace(
            go.Bar(
                name="Mobile",
                x=opcoes,
                y=[round(contagem_mobile.get(o, 0) / total_m * 100, 1) for o in opcoes],
                marker_color="#e63946",
            )
        )
    if contagem_desktop:
        total_d = sum(contagem_desktop.values()) or 1
        fig.add_trace(
            go.Bar(
                name="Desktop",
                x=opcoes,
                y=[round(contagem_desktop.get(o, 0) / total_d * 100, 1) for o in opcoes],
                marker_color="#264653",
            )
        )

    fig.update_layout(
        title=titulo,
        barmode="group",
        yaxis_title="% de respondentes",
        xaxis=dict(tickangle=-15),
        height=420,
        margin=dict(b=140),
        legend=dict(orientation="h", yanchor="bottom", y=-0.55),
    )
    return fig


def resumir_outros_com_ia(pergunta_titulo, outros_mobile, outros_desktop):
    linhas = []
    for texto in outros_mobile or []:
        linhas.append(f"(Mobile) {texto}")
    for texto in outros_desktop or []:
        linhas.append(f"(Desktop) {texto}")
    if not linhas:
        return None
    prompt = PROMPT_OUTROS.format(pergunta=pergunta_titulo)
    return chamar_gemini(None, prompt, "\n".join(linhas))


# ── Session state (novo módulo) ─────────────────────────────────────────────

for key, default in [
    ("insider_analise_pronta", False),
    ("insider_resultados", {}),
    ("insider_resumos_ia", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def _reset_insider_state():
    st.session_state.insider_analise_pronta = False
    st.session_state.insider_resultados = {}
    st.session_state.insider_resumos_ia = {}


# ── Session state (NPS, original) ───────────────────────────────────────────
>>>>>>> 343162d (feat: change sheet format & compile desk and mobile analysis)

for key, default in [
    ("analise_pronta", False),
    ("resultado_final", ""),
    ("tabelas", {}),
    ("tendencia_mobile", {}),
    ("tendencia_desktop", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── App ───────────────────────────────────────────────────────────────────────

if check_password():
<<<<<<< HEAD
    st.set_page_config(page_title="Analisador NPS Track&Field", layout="wide")
    st.title("Analisador de NPS")
    st.caption("Track&Field · Análise automática com Gemini")

    with st.sidebar:
        st.header("Configurações")
        mobile_file = st.file_uploader("Planilha Mobile", type=["xlsx"])
        desktop_file = st.file_uploader("Planilha Desktop", type=["xlsx"])
        st.divider()
        modo = st.radio(
            "Modo de análise",
            ["Resumo consolidado", "Tendência mensal (6 meses)", "Ambos"],
            index=0,
        )
        iniciar = st.button("Iniciar análise", type="primary", use_container_width=True)

    if iniciar:
        if not mobile_file and not desktop_file:
            st.warning("Envie pelo menos uma planilha")
        else:
            # client = genai.Client(api_key=GEMINI_API_KEY)
            client = ""
            st.subheader("Progresso da análise")

            etapas = []
            if mobile_file:
                etapas.append(("Mobile", mobile_file))
            if desktop_file:
                etapas.append(("Desktop", desktop_file))

            fazer_resumo = modo in ("Resumo consolidado", "Ambos")
            fazer_tendencia = modo in ("Tendência mensal", "Ambos")

            # Contagem total de chamadas para a barra de progresso
            dfs = {}
            for tipo, file in etapas:
                dfs[tipo] = carregar_df_bruto(file)

            total_chamadas = 0
            meses_por_canal = {}
            if fazer_tendencia:
                for tipo in dfs:
                    meses = carregar_comentarios_por_mes(dfs[tipo])
                    meses_por_canal[tipo] = meses
                    total_chamadas += len(meses)
            if fazer_resumo:
                total_chamadas += len(etapas) + 1  # parciais + final

            progresso_atual = 0
            progress = st.progress(0)
            status = st.empty()

            temp_tabelas = {}
            resumos_parciais = []
            temp_tend_mobile = {}
            temp_tend_desktop = {}

            for tipo, df_bruto in dfs.items():
                # Tabelas de notas/facilidade (sem chamar Gemini)
                notas = calcular_notas(df_bruto)
                temp_tabelas[tipo] = {
                    "notas": notas,
                    "facilidade": calcular_facilidade(df_bruto),
                    "nps": calcular_nps_por_notas(notas),
                }

                # ── Tendência mensal ──────────────────────────────────────────
                if fazer_tendencia:
                    meses = meses_por_canal[tipo]
                    tend_resultado = {}
                    for periodo, comentarios in meses.items():
                        status.info(
                            f"Tendência {tipo} — {periodo} ({len(comentarios)} comentários)"
                        )
                        tend_resultado[periodo] = chamar_gemini_tendencia(
                            client, comentarios
                        )
                        progresso_atual += 1
                        progress.progress(progresso_atual / total_chamadas)
                        time.sleep(1)  # evita burst na quota

                    if tipo == "Mobile":
                        temp_tend_mobile = tend_resultado
                    else:
                        temp_tend_desktop = tend_resultado

                # ── Resumo consolidado ────────────────────────────────────────
                if fazer_resumo:
                    status.info(f"Resumo consolidado {tipo}")
                    comentarios_todos = carregar_comentarios(df_bruto)
                    resumo = chamar_gemini(
                        client,
                        PROMPT_PARCIAL + f"\nCanal: {tipo}",
                        "\n".join(comentarios_todos),
                    )
                    resumos_parciais.append(f"{tipo}:\n{resumo}")
                    progresso_atual += 1
                    progress.progress(progresso_atual / total_chamadas)

            if fazer_resumo and resumos_parciais:
                status.info("Gerando resumo final consolidado")
                resultado = chamar_gemini(
                    client, PROMPT_FINAL, "\n\n".join(resumos_parciais)
                )
                st.session_state.resultado_final = resultado
                progresso_atual += 1
                progress.progress(progresso_atual / total_chamadas)

            st.session_state.tabelas = temp_tabelas
            st.session_state.tendencia_mobile = temp_tend_mobile
            st.session_state.tendencia_desktop = temp_tend_desktop
            st.session_state.analise_pronta = True

            progress.progress(1.0)
            status.success("Análise concluída!")

    # ── Resultados ─────────────────────────────────────────────────────────────

    if st.session_state.analise_pronta:
        st.divider()

        # ── Tendência mensal ──────────────────────────────────────────────────
        tend_mob = st.session_state.tendencia_mobile
        tend_desk = st.session_state.tendencia_desktop

        if tend_mob or tend_desk:
            st.subheader("Tendência de categorias por mês")
            st.caption(
                "Percentual de comentários que menciona cada tema por mês. "
                "Um comentário pode citar mais de um tema, então os valores não somam 100%."
            )

            if tend_mob and tend_desk:
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(
                        gerar_grafico_tendencia(tend_mob, "Mobile — evolução mensal"),
                        use_container_width=True,
                    )
                with c2:
                    st.plotly_chart(
                        gerar_grafico_tendencia(tend_desk, "Desktop — evolução mensal"),
                        use_container_width=True,
                    )
            elif tend_mob:
                st.plotly_chart(
                    gerar_grafico_tendencia(tend_mob, "Mobile — evolução mensal"),
                    use_container_width=True,
                )
            else:
                st.plotly_chart(
                    gerar_grafico_tendencia(tend_desk, "Desktop — evolução mensal"),
                    use_container_width=True,
                )

            # Tabela numérica opcional
            with st.expander("Ver dados brutos da tendência"):
                for canal, tend in [("Mobile", tend_mob), ("Desktop", tend_desk)]:
                    if tend:
                        df_tend = pd.DataFrame(tend).T
                        df_tend.index.name = "Mês"
                        st.markdown(f"**{canal}**")
                        st.dataframe(
                            df_tend.style.format("{:.0f}%"), use_container_width=True
                        )

        # ── Resumo consolidado ────────────────────────────────────────────────
        if st.session_state.resultado_final:
            st.divider()
            st.subheader("Resultado final consolidado")
            st.text_area("Resumo", st.session_state.resultado_final, height=400)
            st.download_button(
                "Baixar resultado",
                st.session_state.resultado_final,
                file_name="resultado_nps.txt",
                mime="text/plain",
            )

        # ── Tabelas detalhadas ────────────────────────────────────────────────
        ver_tabelas = st.checkbox("Visualizar tabelas detalhadas")
        if ver_tabelas:
            st.divider()
            col1, col2 = st.columns(2)
            tab = st.session_state.tabelas

            if "Mobile" in tab:
                with col1:
                    st.markdown("### Nota experiência MOBILE")
                    df_notas_mob = tab["Mobile"]["notas"].reset_index()
                    df_notas_mob.columns = ["Nota", "Contagem"]
                    st.dataframe(
                        df_notas_mob,
                        use_container_width=True,
                        hide_index=True,
                        height=427,
                    )
                    st.metric("NPS Mobile", f"{tab['Mobile']['nps']}%")

            if "Desktop" in tab:
                with col2:
                    st.markdown("### Nota experiência DESK")
                    df_notas_desk = tab["Desktop"]["notas"].reset_index()
                    df_notas_desk.columns = ["Nota", "Contagem"]
                    st.dataframe(
                        df_notas_desk,
                        use_container_width=True,
                        hide_index=True,
                        height=427,
                    )
                    st.metric("NPS Desktop", f"{tab['Desktop']['nps']}%")

            total_notas = total_promotores = total_detratores = 0
            for canal in ["Mobile", "Desktop"]:
                if canal in tab:
                    notas = tab[canal]["notas"]
                    total_notas += notas.sum()
                    total_promotores += notas.loc[9:10].sum()
                    total_detratores += notas.loc[0:6].sum()

            nps_geral = (
                int(((total_promotores - total_detratores) / total_notas) * 100)
                if total_notas > 0
                else 0
            )

            _, col_centro, _ = st.columns([1, 2, 1])
            with col_centro:
                st.metric("NPS Geral", f"{nps_geral}%")

            st.markdown("---")
            col3, col4 = st.columns(2)
            if "Mobile" in tab:
                with col3:
                    st.markdown("### Facilidade MOBILE")
                    df_facil_mob = tab["Mobile"]["facilidade"].reset_index()
                    df_facil_mob.columns = ["Classificação", "Respostas"]
                    st.dataframe(
                        df_facil_mob, use_container_width=True, hide_index=True
                    )

            if "Desktop" in tab:
                with col4:
                    st.markdown("### Facilidade DESK")
                    df_facil_desk = tab["Desktop"]["facilidade"].reset_index()
                    df_facil_desk.columns = ["Classificação", "Respostas"]
                    st.dataframe(
                        df_facil_desk, use_container_width=True, hide_index=True
                    )
=======
    st.set_page_config(page_title="Analisador de Pesquisas Track&Field", layout="wide")
    st.title("Analisador de Pesquisas")
    st.caption("Track&Field · Análise automática com Gemini")

    tipo_analise = st.sidebar.selectbox(
        "Tipo de pesquisa",
        [
            "NPS",
            "Intenção de saída - PDP",
            "Intenção de saída - Carrinho",
            "Progressive Profile",
        ],
    )
    st.sidebar.divider()

    LABEL_PARA_CHAVE = {
        "Intenção de saída - PDP": "PDP",
        "Intenção de saída - Carrinho": "CARRINHO",
        "Progressive Profile": "PROGRESSIVE",
    }

    # ═══════════════════════════════════════════════════════════════════════
    # MODO 1: NPS (lógica original, inalterada)
    # ═══════════════════════════════════════════════════════════════════════
    if tipo_analise == "NPS":
        with st.sidebar:
            st.header("Configurações")
            mobile_file = st.file_uploader("Planilha Mobile", type=["xlsx"])
            desktop_file = st.file_uploader("Planilha Desktop", type=["xlsx"])
            st.divider()
            modo = st.radio(
                "Modo de análise",
                ["Resumo consolidado", "Tendência mensal (6 meses)", "Ambos"],
                index=0,
            )
            iniciar = st.button("Iniciar análise", type="primary", use_container_width=True)

        if iniciar:
            if not mobile_file and not desktop_file:
                st.warning("Envie pelo menos uma planilha")
            else:
                # client = genai.Client(api_key=GEMINI_API_KEY)
                client = ""
                st.subheader("Progresso da análise")

                etapas = []
                if mobile_file:
                    etapas.append(("Mobile", mobile_file))
                if desktop_file:
                    etapas.append(("Desktop", desktop_file))

                fazer_resumo = modo in ("Resumo consolidado", "Ambos")
                fazer_tendencia = modo in ("Tendência mensal", "Ambos")

                # Contagem total de chamadas para a barra de progresso
                dfs = {}
                for tipo, file in etapas:
                    dfs[tipo] = carregar_df_bruto(file)

                total_chamadas = 0
                meses_por_canal = {}
                if fazer_tendencia:
                    for tipo in dfs:
                        meses = carregar_comentarios_por_mes(dfs[tipo])
                        meses_por_canal[tipo] = meses
                        total_chamadas += len(meses)
                if fazer_resumo:
                    total_chamadas += len(etapas) + 1  # parciais + final

                progresso_atual = 0
                progress = st.progress(0)
                status = st.empty()

                temp_tabelas = {}
                resumos_parciais = []
                temp_tend_mobile = {}
                temp_tend_desktop = {}

                for tipo, df_bruto in dfs.items():
                    # Tabelas de notas/facilidade (sem chamar Gemini)
                    notas = calcular_notas(df_bruto)
                    temp_tabelas[tipo] = {
                        "notas": notas,
                        "facilidade": calcular_facilidade(df_bruto),
                        "nps": calcular_nps_por_notas(notas),
                    }

                    # ── Tendência mensal ──────────────────────────────────────────
                    if fazer_tendencia:
                        meses = meses_por_canal[tipo]
                        tend_resultado = {}
                        for periodo, comentarios in meses.items():
                            status.info(
                                f"Tendência {tipo} - {periodo} ({len(comentarios)} comentários)"
                            )
                            tend_resultado[periodo] = chamar_gemini_tendencia(
                                client, comentarios
                            )
                            progresso_atual += 1
                            progress.progress(progresso_atual / total_chamadas)
                            time.sleep(1)  # evita burst na quota

                        if tipo == "Mobile":
                            temp_tend_mobile = tend_resultado
                        else:
                            temp_tend_desktop = tend_resultado

                    # ── Resumo consolidado ────────────────────────────────────────
                    if fazer_resumo:
                        status.info(f"Resumo consolidado {tipo}")
                        comentarios_todos = carregar_comentarios(df_bruto)
                        resumo = chamar_gemini(
                            client,
                            PROMPT_PARCIAL + f"\nCanal: {tipo}",
                            "\n".join(comentarios_todos),
                        )
                        resumos_parciais.append(f"{tipo}:\n{resumo}")
                        progresso_atual += 1
                        progress.progress(progresso_atual / total_chamadas)

                if fazer_resumo and resumos_parciais:
                    status.info("Gerando resumo final consolidado")
                    resultado = chamar_gemini(
                        client, PROMPT_FINAL, "\n\n".join(resumos_parciais)
                    )
                    st.session_state.resultado_final = resultado
                    progresso_atual += 1
                    progress.progress(progresso_atual / total_chamadas)

                st.session_state.tabelas = temp_tabelas
                st.session_state.tendencia_mobile = temp_tend_mobile
                st.session_state.tendencia_desktop = temp_tend_desktop
                st.session_state.analise_pronta = True

                progress.progress(1.0)
                status.success("Análise concluída!")

        # ── Resultados ─────────────────────────────────────────────────────────────

        if st.session_state.analise_pronta:
            st.divider()

            # ── Tendência mensal ──────────────────────────────────────────────────
            tend_mob = st.session_state.tendencia_mobile
            tend_desk = st.session_state.tendencia_desktop

            if tend_mob or tend_desk:
                st.subheader("Tendência de categorias por mês")
                st.caption(
                    "Percentual de comentários que menciona cada tema por mês. "
                    "Um comentário pode citar mais de um tema, então os valores não somam 100%."
                )

                if tend_mob and tend_desk:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.plotly_chart(
                            gerar_grafico_tendencia(tend_mob, "Mobile - evolução mensal"),
                            use_container_width=True,
                        )
                    with c2:
                        st.plotly_chart(
                            gerar_grafico_tendencia(tend_desk, "Desktop - evolução mensal"),
                            use_container_width=True,
                        )
                elif tend_mob:
                    st.plotly_chart(
                        gerar_grafico_tendencia(tend_mob, "Mobile - evolução mensal"),
                        use_container_width=True,
                    )
                else:
                    st.plotly_chart(
                        gerar_grafico_tendencia(tend_desk, "Desktop - evolução mensal"),
                        use_container_width=True,
                    )

                # Tabela numérica opcional
                with st.expander("Ver dados brutos da tendência"):
                    for canal, tend in [("Mobile", tend_mob), ("Desktop", tend_desk)]:
                        if tend:
                            df_tend = pd.DataFrame(tend).T
                            df_tend.index.name = "Mês"
                            st.markdown(f"**{canal}**")
                            st.dataframe(
                                df_tend.style.format("{:.0f}%"), use_container_width=True
                            )

            # ── Resumo consolidado ────────────────────────────────────────────────
            if st.session_state.resultado_final:
                st.divider()
                st.subheader("Resultado final consolidado")
                st.text_area("Resumo", st.session_state.resultado_final, height=400)
                st.download_button(
                    "Baixar resultado",
                    st.session_state.resultado_final,
                    file_name="resultado_nps.txt",
                    mime="text/plain",
                )

            # ── Tabelas detalhadas ────────────────────────────────────────────────
            ver_tabelas = st.checkbox("Visualizar tabelas detalhadas")
            if ver_tabelas:
                st.divider()
                col1, col2 = st.columns(2)
                tab = st.session_state.tabelas

                if "Mobile" in tab:
                    with col1:
                        st.markdown("### Nota experiência MOBILE")
                        df_notas_mob = tab["Mobile"]["notas"].reset_index()
                        df_notas_mob.columns = ["Nota", "Contagem"]
                        st.dataframe(
                            df_notas_mob,
                            use_container_width=True,
                            hide_index=True,
                            height=427,
                        )
                        st.metric("NPS Mobile", f"{tab['Mobile']['nps']}%")

                if "Desktop" in tab:
                    with col2:
                        st.markdown("### Nota experiência DESK")
                        df_notas_desk = tab["Desktop"]["notas"].reset_index()
                        df_notas_desk.columns = ["Nota", "Contagem"]
                        st.dataframe(
                            df_notas_desk,
                            use_container_width=True,
                            hide_index=True,
                            height=427,
                        )
                        st.metric("NPS Desktop", f"{tab['Desktop']['nps']}%")

                total_notas = total_promotores = total_detratores = 0
                for canal in ["Mobile", "Desktop"]:
                    if canal in tab:
                        notas = tab[canal]["notas"]
                        total_notas += notas.sum()
                        total_promotores += notas.loc[9:10].sum()
                        total_detratores += notas.loc[0:6].sum()

                nps_geral = (
                    int(((total_promotores - total_detratores) / total_notas) * 100)
                    if total_notas > 0
                    else 0
                )

                _, col_centro, _ = st.columns([1, 2, 1])
                with col_centro:
                    st.metric("NPS Geral", f"{nps_geral}%")

                st.markdown("---")
                col3, col4 = st.columns(2)
                if "Mobile" in tab:
                    with col3:
                        st.markdown("### Facilidade MOBILE")
                        df_facil_mob = tab["Mobile"]["facilidade"].reset_index()
                        df_facil_mob.columns = ["Classificação", "Respostas"]
                        st.dataframe(
                            df_facil_mob, use_container_width=True, hide_index=True
                        )

                if "Desktop" in tab:
                    with col4:
                        st.markdown("### Facilidade DESK")
                        df_facil_desk = tab["Desktop"]["facilidade"].reset_index()
                        df_facil_desk.columns = ["Classificação", "Respostas"]
                        st.dataframe(
                            df_facil_desk, use_container_width=True, hide_index=True
                        )

    # ═══════════════════════════════════════════════════════════════════════
    # MODO 2: Campanhas Insider (PDP / Carrinho / Progressive Profile)
    # ═══════════════════════════════════════════════════════════════════════
    else:
        campanha_chave = LABEL_PARA_CHAVE[tipo_analise]
        campanha_cfg = CAMPANHAS_CONFIG[campanha_chave]

        with st.sidebar:
            st.header("Configurações")
            mobile_file = st.file_uploader(
                "Planilha Mobile", type=["xlsx"], key=f"mobile_{campanha_chave}"
            )
            desktop_file = st.file_uploader(
                "Planilha Desktop", type=["xlsx"], key=f"desktop_{campanha_chave}"
            )
            gerar_ia = st.checkbox(
                "Gerar resumo com IA das respostas abertas (Outros)", value=True
            )

        if not mobile_file and not desktop_file:
            st.info("Envie a planilha Mobile e/ou Desktop na barra lateral para começar.")
        else:
            dfs_brutos = {}
            if mobile_file:
                dfs_brutos["Mobile"] = carregar_df_bruto(mobile_file)
            if desktop_file:
                dfs_brutos["Desktop"] = carregar_df_bruto(desktop_file)

            # ── Filtro de período ────────────────────────────────────────────
            todas_datas = pd.concat(
                [carregar_datas(df) for df in dfs_brutos.values()]
            ).dropna()

            if todas_datas.empty:
                st.error("Não foi possível identificar datas válidas na coluna 'Date'.")
                st.stop()

            data_min = todas_datas.min().date()
            data_max = todas_datas.max().date()

            st.subheader(tipo_analise)
            periodo = st.date_input(
                "Filtrar por período",
                value=(data_min, data_max),
                min_value=data_min,
                max_value=data_max,
                format="DD/MM/YYYY",
            )
            if isinstance(periodo, tuple) and len(periodo) == 2:
                data_ini, data_fim = periodo
            else:
                data_ini, data_fim = data_min, data_max

            iniciar_insider = st.button(
                "Gerar relatório", type="primary", use_container_width=False
            )

            if iniciar_insider:
                dfs_filtrados = {
                    canal: filtrar_por_periodo(df, data_ini, data_fim)
                    for canal, df in dfs_brutos.items()
                }

                resultados = {}
                for pergunta_cfg in campanha_cfg["perguntas"]:
                    entrada = {}
                    for canal, df in dfs_filtrados.items():
                        contagem, outros = classificar_pergunta(df, pergunta_cfg)
                        entrada[canal] = {"contagem": contagem, "outros": outros}
                    resultados[pergunta_cfg["chave"]] = entrada

                st.session_state.insider_resultados = resultados
                st.session_state.insider_analise_pronta = True
                st.session_state.insider_resumos_ia = {}

                if gerar_ia:
                    with st.spinner("Gerando resumo das respostas abertas com IA..."):
                        for pergunta_cfg in campanha_cfg["perguntas"]:
                            entrada = resultados[pergunta_cfg["chave"]]
                            outros_mobile = entrada.get("Mobile", {}).get("outros")
                            outros_desktop = entrada.get("Desktop", {}).get("outros")
                            resumo = resumir_outros_com_ia(
                                pergunta_cfg["titulo"], outros_mobile, outros_desktop
                            )
                            if resumo:
                                st.session_state.insider_resumos_ia[
                                    pergunta_cfg["chave"]
                                ] = resumo

            # ── Exibição dos resultados ──────────────────────────────────────
            if st.session_state.insider_analise_pronta:
                st.divider()
                resultados = st.session_state.insider_resultados

                for pergunta_cfg in campanha_cfg["perguntas"]:
                    chave = pergunta_cfg["chave"]
                    if chave not in resultados:
                        continue
                    entrada = resultados[chave]

                    contagem_mobile = entrada.get("Mobile", {}).get("contagem")
                    contagem_desktop = entrada.get("Desktop", {}).get("contagem")
                    outros_mobile = entrada.get("Mobile", {}).get("outros") or []
                    outros_desktop = entrada.get("Desktop", {}).get("outros") or []

                    if contagem_mobile is None and contagem_desktop is None:
                        continue  # pergunta não existe nesta planilha (ex: lógica condicional)

                    st.markdown(f"### {pergunta_cfg['titulo']}")
                    if pergunta_cfg["opcoes"] is None:
                        st.caption(
                            "⚠️ Lista oficial de opções ainda não confirmada - exibindo "
                            "distribuição bruta das respostas recebidas."
                        )

                    n_mobile = sum(contagem_mobile.values()) if contagem_mobile else 0
                    n_desktop = sum(contagem_desktop.values()) if contagem_desktop else 0
                    st.caption(f"Respostas: Mobile = {n_mobile} · Desktop = {n_desktop}")

                    if (contagem_mobile and any(contagem_mobile.values())) or (
                        contagem_desktop and any(contagem_desktop.values())
                    ):
                        st.plotly_chart(
                            gerar_grafico_distribuicao(
                                contagem_mobile, contagem_desktop, pergunta_cfg["titulo"]
                            ),
                            use_container_width=True,
                        )
                    else:
                        st.caption("Sem respostas nas opções mapeadas para este período.")

                    total_outros = len(outros_mobile) + len(outros_desktop)
                    if total_outros > 0:
                        with st.expander(
                            f"Ver respostas abertas / \"Outros\" ({total_outros})"
                        ):
                            resumo_ia = st.session_state.insider_resumos_ia.get(chave)
                            if resumo_ia:
                                st.markdown("**Resumo gerado por IA**")
                                st.text(resumo_ia)
                                st.markdown("---")

                            if outros_mobile:
                                st.markdown(f"**Mobile ({len(outros_mobile)})**")
                                for texto in outros_mobile:
                                    st.markdown(f"- {texto}")
                            if outros_desktop:
                                st.markdown(f"**Desktop ({len(outros_desktop)})**")
                                for texto in outros_desktop:
                                    st.markdown(f"- {texto}")

                    st.divider()
>>>>>>> 343162d (feat: change sheet format & compile desk and mobile analysis)
