import re
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

MAX_CONTENT_CHARS = 16000
EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
BIORXIV_DETAILS_URL = "https://api.biorxiv.org/details/biorxiv"
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>?#]+", re.IGNORECASE)

SECTION_HEADINGS = {
    "abstract": "Abstract",
    "summary": "Abstract",
    "introduction": "Introduction",
    "background": "Introduction",
    "methods": "Methods",
    "materials and methods": "Methods",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
}

STOP_HEADINGS = {
    "references",
    "acknowledgements",
    "acknowledgments",
    "funding",
    "author information",
    "ethics declarations",
    "supplementary information",
    "additional information",
}


def extract_doi(*texts: str) -> str:
    for text in texts:
        match = DOI_RE.search(text or "")
        if match:
            return match.group(0).rstrip(").,;]")
    return ""


async def fetch_open_article_content(client: httpx.AsyncClient, doi: str) -> tuple[str, str]:
    content = await _fetch_europe_pmc_content(client, doi)
    if content:
        return content, "Europe PMC"

    content = await _fetch_biorxiv_content(client, doi)
    if content:
        return content, "bioRxiv API"

    return "", ""


async def _fetch_europe_pmc_content(client: httpx.AsyncClient, doi: str) -> str:
    try:
        resp = await client.get(
            EUROPE_PMC_SEARCH_URL,
            params={"query": f"DOI:{doi}", "format": "json", "resultType": "core"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        print(f"  [警告] Europe PMC 兜底失败: {e}")
        return ""

    result = _first_europe_pmc_result(data)
    if not result:
        return ""

    pmcid = result.get("pmcid", "")
    if pmcid and result.get("inEPMC") == "Y":
        full_text = await _fetch_europe_pmc_full_text(client, pmcid)
        if full_text:
            return full_text

    return _format_abstract_text(result.get("abstractText", ""))


async def _fetch_europe_pmc_full_text(client: httpx.AsyncClient, pmcid: str) -> str:
    try:
        resp = await client.get(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return ""

    return extract_europe_pmc_xml_text(resp.text)


async def _fetch_biorxiv_content(client: httpx.AsyncClient, doi: str) -> str:
    encoded_doi = quote(doi, safe="/.")
    try:
        resp = await client.get(f"{BIORXIV_DETAILS_URL}/{encoded_doi}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        print(f"  [警告] bioRxiv API 兜底失败: {e}")
        return ""

    return _format_abstract_text(_extract_biorxiv_abstract(data))


def extract_europe_pmc_xml_text(xml: str, max_chars: int = MAX_CONTENT_CHARS) -> str:
    soup = BeautifulSoup(xml, "xml")
    chunks = []

    abstract = soup.find("abstract")
    if abstract:
        chunks.append("## Abstract")
        chunks.append(abstract.get_text(" ", strip=True))

    body = soup.find("body")
    if body:
        chunks.extend(_extract_jats_sections(body))

    return _clean_lines("\n".join(chunks))[:max_chars]


def _first_europe_pmc_result(data: dict) -> dict:
    result_list = data.get("resultList", {})
    results = result_list.get("result", [])
    if not results:
        return {}
    return results[0]


def _extract_biorxiv_abstract(data: dict) -> str:
    collection = data.get("collection", [])
    if not collection:
        return ""
    return collection[-1].get("abstract", "")


def _format_abstract_text(text: str) -> str:
    cleaned = _clean_lines(text)
    if not cleaned:
        return ""
    return f"## Abstract\n{cleaned}"


def _extract_jats_sections(body) -> list[str]:
    chunks = []
    for section in body.find_all("sec", recursive=False):
        title_tag = section.find("title", recursive=False)
        title = title_tag.get_text(" ", strip=True) if title_tag else ""
        normalized = _normalize_heading(title)
        if normalized in STOP_HEADINGS:
            break

        heading = SECTION_HEADINGS.get(normalized, title)
        if heading:
            chunks.append(f"## {heading}")

        for paragraph in section.find_all("p", recursive=False):
            text = paragraph.get_text(" ", strip=True)
            if text:
                chunks.append(text)
    return chunks


def _normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z ]+", "", text.lower()).strip()


def _clean_lines(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
