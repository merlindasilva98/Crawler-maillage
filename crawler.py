import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import networkx as nx
import xml.etree.ElementTree as ET


def normalize_url(url):
    parsed = urlparse(url)
    path = parsed.path
    if not path.endswith("/") and '.' not in path.split("/")[-1]:
        path += "/"
    netloc = parsed.netloc.lower().replace("www.", "")
    return urlunparse((parsed.scheme, netloc, path, '', '', ''))


def is_internal_link(link, domain):
    parsed = urlparse(link)
    netloc = parsed.netloc.lower().replace("www.", "")
    return netloc == '' or netloc == domain


def is_valid_link(link):
    link = link.lower()
    if link.startswith(("mailto:", "tel:", "javascript:")):
        return False

    excluded_extensions = [
        ".pdf", ".jpg", ".jpeg", ".png", ".css", ".js", ".svg", ".ico",
        ".webp", ".mp4", ".avi", ".mov", ".zip", ".rar", ".json", ".xml"
    ]
    if any(link.endswith(ext) for ext in excluded_extensions):
        return False

    excluded_keywords = [
        "cookie", "privacy", "terms", "policy", "facebook", "twitter",
        "linkedin", "instagram", "tiktok", "pinterest", "utm_", "tagmanager",
        "wp-content", "wp-json", "wp-admin", "wp-includes",
        "administrator", "components", "media", "modules", "themes",
        "feed", "login", "logout", "signup", "register", "account"
    ]
    if any(keyword in link for keyword in excluded_keywords):
        return False

    return True


def fetch_sitemap(start_url):
    domain_root = urlparse(start_url).scheme + "://" + urlparse(start_url).netloc
    sitemap_url = urljoin(domain_root, "/sitemap.xml")

    try:
        response = requests.get(sitemap_url, timeout=5)
        if response.status_code != 200 or "xml" not in response.headers.get("Content-Type", ""):
            print("⚠️ Pas de sitemap détecté.")
            return []

        sitemap_urls = []
        tree = ET.fromstring(response.content)
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in tree.findall(".//ns:loc", namespaces=namespace):
            sitemap_urls.append(loc.text.strip())

        print(f"📄 Sitemap détecté : {len(sitemap_urls)} URLs importées.")
        return sitemap_urls

    except Exception:
        print("⚠️ Échec lors de la lecture du sitemap.")
        return []


async def fetch(session, url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; WebCrawler/1.0)"}
    try:
        async with session.get(url, timeout=8, headers=headers) as response:
            if response.status != 200:
                return None
            if "text/html" not in response.headers.get("Content-Type", ""):
                return None
            return await response.text()
    except Exception:
        return None


async def crawl_async(start_url, max_depth):
    visited = set()
    graph = nx.DiGraph()
    domain = urlparse(start_url).netloc.lower().replace("www.", "")
    queue = [(normalize_url(start_url), 0)]

    async with aiohttp.ClientSession() as session:
        while queue:
            current_url, current_depth = queue.pop(0)
            if current_url in visited or current_depth > max_depth:
                continue

            visited.add(current_url)
            html = await fetch(session, current_url)
            if html is None:
                continue

            soup = BeautifulSoup(html, "html.parser")

            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href")
                if not href:
                    continue
                absolute_link = normalize_url(urljoin(current_url, href))
                if is_internal_link(absolute_link, domain) and is_valid_link(absolute_link):
                    anchor_text = a_tag.get_text(strip=True)
                    graph.add_edge(current_url, absolute_link, label=anchor_text)
                    if absolute_link not in visited:
                        queue.append((absolute_link, current_depth + 1))

    return graph


def crawl(start_url, max_depth):
    print(f"🔍 Démarrage du crawl asynchrone sur : {start_url}")
    graph = asyncio.run(crawl_async(start_url, max_depth))
    print(f"✅ Crawl terminé. {len(graph.nodes)} pages découvertes.")

    depths = {}
    for node in graph.nodes:
        try:
            depth = nx.shortest_path_length(graph, source=normalize_url(start_url), target=node)
            depths[node] = depth
        except nx.NetworkXNoPath:
            depths[node] = -1

    sitemap_urls = fetch_sitemap(start_url)
    for url in sitemap_urls:
        url = normalize_url(url)
        if url not in graph:
            graph.add_node(url)

    return graph, depths, sitemap_urls