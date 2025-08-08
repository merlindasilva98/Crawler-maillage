import networkx as nx
from pyvis.network import Network
import tempfile
from pathlib import Path

# Couleurs par profondeur
depth_colors = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

def render_graph(graph, depths, min_depth=0, max_depth=10):
    """
    Rend le graphe en HTML avec Pyvis.
    """
    from pyvis.network import Network
    import tempfile
    from pathlib import Path

    net = Network(height="800px", width="100%", directed=True, notebook=False)
    net.barnes_hut(gravity=-25000, central_gravity=0.3, spring_length=120)

    # Garde les mêmes positions entre sessions (drag & drop persistant)
    net.set_options("""
    var options = {
      "nodes": {
        "physics": false
      },
      "physics": {
        "enabled": true,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "centralGravity": 0.01,
          "springLength": 120,
          "springConstant": 0.08
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": true
      }
    }
    """)

    filtered_nodes = [node for node, depth in depths.items() if min_depth <= depth <= max_depth]

    # Ajout des nœuds
    for node in filtered_nodes:
        depth = depths.get(node, -1)
        if depth == -1:
            color = "#cccccc"  # gris clair pour les pages isolées
        else:
            color = depth_colors[depth % len(depth_colors)]
        net.add_node(node, label=node, color=color, title=f"Profondeur {depth if depth >= 0 else 'isolée'}")

    # Ajout des arêtes
    for source, target, data in graph.edges(data=True):
        if source in filtered_nodes and target in filtered_nodes:
            is_reciprocal = graph.has_edge(target, source)
            color = "red" if is_reciprocal else "gray"
            net.add_edge(source, target, color=color, title=data.get("label", ""), arrows="to")

    # Interaction personnalisée : clique sur un nœud = masque les autres arêtes
    custom_js = """
    <script type="text/javascript">
    function filterEdgesOnClick(network) {
        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                let selectedNode = params.nodes[0];
                let allEdges = network.body.data.edges.get();
                let visibleEdges = [];

                allEdges.forEach(function (edge) {
                    if (edge.from === selectedNode || edge.to === selectedNode) {
                        visibleEdges.push({...edge, hidden: false, width: 2});
                    } else {
                        visibleEdges.push({...edge, hidden: true});
                    }
                });

                network.body.data.edges.update(visibleEdges);
            } else {
                // Si on clique dans le vide : tout réafficher
                let allEdges = network.body.data.edges.get();
                let restoredEdges = allEdges.map(e => ({...e, hidden: false, width: 1}));
                network.body.data.edges.update(restoredEdges);
            }
        });
    }
    filterEdgesOnClick(network);
    </script>
    """

    # CSS pour forcer la largeur en plein écran
    custom_css = """
    <style>
    html, body, #mynetwork {
        width: 100vw !important;
        max-width: 100% !important;
        margin: 0;
        padding: 0;
    }
    </style>
    """

    # Génère le HTML final
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding="utf-8") as tmp_file:
        net.save_graph(tmp_file.name)
        html_content = Path(tmp_file.name).read_text(encoding="utf-8")
        html_content = html_content.replace("</body>", custom_js + "</body>")
        html_content = html_content.replace("<body>", "<body>" + custom_css)
        tmp_path = Path(tmp_file.name)
        tmp_path.write_text(html_content, encoding="utf-8")

    return str(tmp_path)