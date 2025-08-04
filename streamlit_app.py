import streamlit as st
from crawler import crawl
from crawler import normalize_url
from renderer import render_graph
from pathlib import Path

st.set_page_config(page_title="Graphe de Maillage Interne", layout="wide")
st.title("🔗 Visualisation du Maillage Interne")

st.markdown("""
Ce petit outil vous permet de :
- Crawler un site web interne
- Visualiser les liens internes (avec les liens réciproques en **rouge**)
- Colorer les pages selon leur **profondeur** dans le maillage
- Filtrer les pages affichées selon leur **niveau de profondeur**
""")

# Zone de saisie
start_url = st.text_input("URL de départ", value="https://www.menuiserie-brahy.be/")
max_depth = st.slider("Profondeur maximale de crawl", min_value=1, max_value=10, value=3)

if st.button("Lancer le crawl"):
    with st.spinner("Crawl en cours..."):
        try:
            graph, depths, sitemap_urls = crawl(start_url, max_depth)
            st.session_state.graph = graph
            st.session_state.depths = depths
            st.session_state.sitemap_urls = sitemap_urls
            st.success(f"Crawl terminé. {len(graph.nodes)} pages trouvées.")
        except Exception as e:
            st.error(f"Erreur pendant le crawl : {e}")

    # 🔍 Infos Sitemap
    sitemap_set = set(normalize_url(url) for url in sitemap_urls)
    isolated_from_sitemap = [url for url in sitemap_set if url in graph.nodes and graph.degree(url) == 0]
    num_total = len(sitemap_set)
    num_isolated = len(isolated_from_sitemap)

    with st.expander("📄 Infos Sitemap"):
        st.markdown(f"""
        - **Total d'URLs dans le sitemap** : `{num_total}`
        - **Pages du sitemap non reliées dans le maillage interne** : `{num_isolated}`
        """)

# Affichage du graphe
if "graph" in st.session_state and "depths" in st.session_state:
    st.markdown("### 🎨 Filtres d’affichage")

    min_depth = st.slider("Afficher à partir de la profondeur", 0, max_depth, 0)
    max_depth_filter = st.slider("Afficher jusqu’à la profondeur", min_depth, max_depth, max_depth)

    if st.button("Générer le graphe filtré"):
        with st.spinner("Génération du graphe..."):
            html_path = render_graph(st.session_state.graph, st.session_state.depths, min_depth, max_depth_filter)
            st.success("Graphe généré !")
            st.components.v1.html(Path(html_path).read_text(), height=800, scrolling=True)

    st.markdown("### 🟡 Légende des couleurs de profondeur")
    from renderer import depth_colors
    for i, color in enumerate(depth_colors):
        st.markdown(f"<span style='color:{color}; font-size: 20px'>⬤</span> Profondeur {i}", unsafe_allow_html=True)