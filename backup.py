import time

import pandas as pd
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
    """Retorna True se o usuário inseriu a senha correta."""

    def password_entered():
        """Verifica se a senha inserida coincide com a do Secrets."""
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

if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    with st.sidebar:
        st.warning("Chave API não encontrada nos Secrets.")
        GEMINI_API_KEY = st.text_input("Insira sua Gemini API Key:", type="password")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    st.error("Por favor, configure a API Key para continuar.")
    st.stop()


MODEL_NAME = "gemini-2.5-flash-lite"

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


def grupo_nps(nota):
    if nota >= 9:
        return "Promotores"
    if nota >= 7:
        return "Neutros"
    return "Detratores"


def carregar_df_bruto(file):
    return pd.read_excel(file, header=14)


def carregar_comentarios(df):
    comentarios = []
    for _, row in df.iterrows():
        try:
            nota = int(row.iloc[4])
        except:
            continue
        comentario = str(row.iloc[6]).strip()
        if not comentario or comentario.lower() == "nan":
            continue
        grupo = grupo_nps(nota)
        comentarios.append(f"{nota}-{comentario} ({grupo})")
    return comentarios


def calcular_notas(df):
    notas = pd.to_numeric(df.iloc[:, 4], errors="coerce").dropna().astype(int)
    return notas.value_counts().reindex(range(0, 11), fill_value=0).sort_index()


def calcular_facilidade(df):
    facilidade = df.iloc[:, 5].astype(str).replace({"nan": "(não respondeu)"})
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


def chamar_gemini(client, prompt, conteudo):
    if USE_MOCK_GEMINI:
        return """
Categorias Mais Citadas:
- Entrega: 30% (Ex: "Atrasou 2 dias")
- Produto: 25% (Ex: "Tecido excelente")
- Atendimento: 20% (Ex: "Vendedor atencioso")
- Outros: 25%

Por Grupo NPS:
- Detratores (0–6): Reclamações sobre logística.
- Neutros (7–8): Gostam da marca, mas acham o frete caro.
- Promotores (9–10): Amam a qualidade das peças.

Sentimento Geral:
- positivo, com foco em qualidade de produto.
""".strip()

    for tentativa in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=f"{prompt}\n\n{conteudo}",
            )

            return response.text

        except Exception as e:
            time.sleep(2)
            if tentativa == 2:
                st.error(f"Erro na API após 3 tentativas: {e}")

    raise RuntimeError("Falha ao chamar Gemini após várias tentativas")


if "analise_pronta" not in st.session_state:
    st.session_state.analise_pronta = False
if "resultado_final" not in st.session_state:
    st.session_state.resultado_final = ""
if "tabelas" not in st.session_state:
    st.session_state.tabelas = {}

if check_password():
    st.set_page_config(page_title="Analisador NPS Track&Field", layout="wide")
    st.title("Analisador de NPS")
    st.caption("Track&Field · Análise automática com Gemini")

    with st.sidebar:
        st.header("Configurações")
        mobile_file = st.file_uploader("Planilha Mobile", type=["xlsx"])
        desktop_file = st.file_uploader("Planilha Desktop", type=["xlsx"])
        st.divider()
        iniciar = st.button("Iniciar análise", type="primary", width="stretch")

    if iniciar:
        if not mobile_file and not desktop_file:
            st.warning("Envie pelo menos uma planilha")
        else:
            client = genai.Client(api_key=GEMINI_API_KEY)
            st.subheader("Progresso da análise")
            progress = st.progress(0)
            status = st.empty()

            resumos_parciais = []
            temp_tabelas = {}
            etapas = []
            if mobile_file:
                etapas.append(("Mobile", mobile_file))
            if desktop_file:
                etapas.append(("Desktop", desktop_file))

            total_etapas = len(etapas) + 1
            for i, (tipo, file) in enumerate(etapas):
                status.info(f"Processando {tipo}")
                df_bruto = carregar_df_bruto(file)

                notas = calcular_notas(df_bruto)

                temp_tabelas[tipo] = {
                    "notas": notas,
                    "facilidade": calcular_facilidade(df_bruto),
                    "nps": calcular_nps_por_notas(notas),
                }

                comentarios = carregar_comentarios(df_bruto)
                resumo = chamar_gemini(
                    client, PROMPT_PARCIAL + f"\nCanal: {tipo}", "\n".join(comentarios)
                )
                resumos_parciais.append(f"{tipo}:\n{resumo}")
                progress.progress((i + 1) / total_etapas)

            status.info("Gerando resumo final")
            resultado = chamar_gemini(
                client, PROMPT_FINAL, "\n\n".join(resumos_parciais)
            )

            st.session_state.resultado_final = resultado
            st.session_state.tabelas = temp_tabelas
            st.session_state.analise_pronta = True

            progress.progress(1.0)
            status.success("Análise concluída")

    if st.session_state.analise_pronta:
        st.divider()
        st.subheader("Resultado final")
        st.text_area("Resumo consolidado", st.session_state.resultado_final, height=400)

        st.download_button(
            "Baixar resultado",
            st.session_state.resultado_final,
            file_name="resultado_nps.txt",
            mime="text/plain",
        )

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
                        df_notas_mob, width="stretch", hide_index=True, height=427
                    )

                    nps_mobile = tab["Mobile"]["nps"]
                    st.metric("NPS Mobile", f"{nps_mobile}%")

            if "Desktop" in tab:
                with col2:
                    st.markdown("### Nota experiência DESK")
                    df_notas_desk = tab["Desktop"]["notas"].reset_index()
                    df_notas_desk.columns = ["Nota", "Contagem"]
                    st.dataframe(
                        df_notas_desk, width="stretch", hide_index=True, height=427
                    )

                    nps_desktop = tab["Desktop"]["nps"]
                    st.metric("NPS Desktop", f"{nps_desktop}%")

            # ----

            total_notas = 0
            total_promotores = 0
            total_detratores = 0

            for canal in ["Mobile", "Desktop"]:
                if canal in tab:
                    notas = tab[canal]["notas"]
                    total_notas += notas.sum()
                    total_promotores += notas.loc[9:10].sum()
                    total_detratores += notas.loc[0:6].sum()

            if total_notas > 0:
                nps_geral = int(
                    ((total_promotores - total_detratores) / total_notas) * 100
                )
            else:
                nps_geral = 0

            # ----

            col_esq, col_centro, col_dir = st.columns([1, 2, 1])

            with col_centro:
                st.metric(label="NPS Geral", value=f"{nps_geral}%")

            st.markdown("---")

            col3, col4 = st.columns(2)
            if "Mobile" in tab:
                with col3:
                    st.markdown("### Facilidade MOBILE")
                    df_facil_mob = tab["Mobile"]["facilidade"].reset_index()
                    df_facil_mob.columns = ["Classificação", "Respostas"]
                    st.dataframe(df_facil_mob, width="stretch", hide_index=True)

            if "Desktop" in tab:
                with col4:
                    st.markdown("### Facilidade DESK")
                    df_facil_desk = tab["Desktop"]["facilidade"].reset_index()
                    df_facil_desk.columns = ["Classificação", "Respostas"]
                    st.dataframe(df_facil_desk, width="stretch", hide_index=True)
