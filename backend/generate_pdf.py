import os
import re
import html
import shutil
import pygments
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

WORKSPACE_DIR = r"c:\Users\skfir\Desktop\Project-1"
ARTIFACT_DIR = r"C:\Users\skfir\.gemini\antigravity-ide\brain\78ad9728-321e-424f-aa7b-a4f66a293ca6"
REPORT_MD_PATH = os.path.join(ARTIFACT_DIR, "signalreport_architectural_report.md")
DOCS_IMG_DIR = os.path.join(WORKSPACE_DIR, "docs_images")
OUTPUT_PDF_PATH = os.path.join(WORKSPACE_DIR, "SignalReport_Architecture_Report.pdf")
ARTIFACT_PDF_PATH = os.path.join(ARTIFACT_DIR, "SignalReport_Architecture_Report.pdf")

# Images source
IMG_SRC_TOPOLOGY = os.path.join(ARTIFACT_DIR, "arch_system_topology_1790063802605.jpg")
IMG_SRC_PIPELINE = os.path.join(ARTIFACT_DIR, "arch_data_pipeline_1790063822943.jpg")
IMG_SRC_SECURITY = os.path.join(ARTIFACT_DIR, "arch_security_flow_1790063915352.jpg")
IMG_SRC_FRONTEND = os.path.join(ARTIFACT_DIR, "arch_frontend_gui_1790064009101.jpg")

def copy_images():
    os.makedirs(DOCS_IMG_DIR, exist_ok=True)
    images = [
        (IMG_SRC_TOPOLOGY, "arch_system_topology.jpg"),
        (IMG_SRC_PIPELINE, "arch_data_pipeline.jpg"),
        (IMG_SRC_SECURITY, "arch_security_flow.jpg"),
        (IMG_SRC_FRONTEND, "arch_frontend_gui.jpg"),
    ]
    for src, name in images:
        dst = os.path.join(DOCS_IMG_DIR, name)
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            print(f"Copied {name} -> {dst}")
        else:
            print(f"Warning: source image missing: {src}")

def highlight_code(code, lang, attrs):
    if lang == "mermaid":
        return f'<div class="mermaid-container"><div class="mermaid">\n{code}\n</div></div>'
    try:
        lexer = get_lexer_by_name(lang, stripall=True)
    except Exception:
        lexer = TextLexer()
    formatter = HtmlFormatter(nowrap=True)
    highlighted = pygments.highlight(code, lexer, formatter)
    lang_display = html.escape(lang.upper() if lang else "CODE")
    return f'<div class="code-block-wrapper"><div class="code-lang-tag">{lang_display}</div><pre><code class="highlight">{highlighted}</code></pre></div>'

def build_pdf():
    print("Step 1: Copying images to docs_images folder...", flush=True)
    copy_images()

    print(f"Step 2: Reading markdown report from: {REPORT_MD_PATH}", flush=True)
    with open(REPORT_MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Relative paths for images from the HTML file in WORKSPACE_DIR
    rel_topology = "docs_images/arch_system_topology.jpg"
    rel_pipeline = "docs_images/arch_data_pipeline.jpg"
    rel_security = "docs_images/arch_security_flow.jpg"
    rel_frontend = "docs_images/arch_frontend_gui.jpg"

    # Figure Cards
    fig_topology_html = f'''
    <div class="figure-card">
        <div class="figure-badge">SYSTEM ARCHITECTURE GUI &bull; TELEMETRY</div>
        <div class="figure-img-wrap">
            <img src="{rel_topology}" alt="SignalReport System Topology & Infrastructure Monitoring GUI" />
        </div>
        <div class="figure-caption">
            <strong>Figure 1.1: SignalReport System Topology & Real-Time Infrastructure Monitoring GUI</strong> &mdash; 
            Operations control view demonstrating the microservices orchestration: React frontend client layer, 
            FastAPI async gateway with SSL termination and rate limiting, internal service mesh (AI inference engine, 
            reporting, audit logging), PostgreSQL connection pool, and asynchronous execution pipeline.
        </div>
    </div>
    '''

    fig_pipeline_html = f'''
    <div class="figure-card">
        <div class="figure-badge">DATA INGESTION &bull; STREAMING PIPELINE GUI</div>
        <div class="figure-img-wrap">
            <img src="{rel_pipeline}" alt="Enterprise Real-Time News Ingestion & NLP Analytics Pipeline GUI" />
        </div>
        <div class="figure-caption">
            <strong>Figure 2.1: Enterprise Real-Time News Ingestion & NLP Analytics Pipeline GUI</strong> &mdash; 
            End-to-end telemetry and processing topology showing live news ingestion from syndicated APIs, webhooks, 
            and RSS streams, NLP entity tagging and sentiment scoring, topic classification, deduplication engine, 
            and asynchronous database persistence alongside live client WebSocket dispatch.
        </div>
    </div>
    '''

    fig_frontend_html = f'''
    <div class="figure-card">
        <div class="figure-badge">FRONTEND ARCHITECTURE &bull; EDITORIAL GUI</div>
        <div class="figure-img-wrap">
            <img src="{rel_frontend}" alt="SignalReport Swiss Editorial News Intelligence Dashboard GUI" />
        </div>
        <div class="figure-caption">
            <strong>Figure 4.1: SignalReport Swiss Editorial News Intelligence Dashboard GUI</strong> &mdash; 
            Production UI layout exhibiting Swiss modernist typography, category navigation (Tech Trends, Markets, 
            Politics, Energy), card-based article presentation with real-time sentiment tags, optimistic bookmarking/read tracking, 
            market telemetry ticker, and user session activity monitoring.
        </div>
    </div>
    '''

    fig_security_html = f'''
    <div class="figure-card">
        <div class="figure-badge">SECURITY ARCHITECTURE &bull; MULTI-LAYER DEFENSE BLUEPRINT</div>
        <div class="figure-img-wrap">
            <img src="{rel_security}" alt="Enterprise Multi-Layer Defense Architecture & Token Lifecycle Blueprint" />
        </div>
        <div class="figure-caption">
            <strong>Figure 6.1: Enterprise Multi-Layer Defense Architecture & Token Lifecycle Blueprint</strong> &mdash; 
            Comprehensive technical schematic detailing the Cloudflare Edge proxy layer (WAF, CIDR verification, rate limiting), 
            Identity & Access Management (JWT Bearer tokens with Refresh Token Rotation and reuse detection), 
            HTTP security headers enforcement (HSTS, CSP, XFO), and encrypted PostgreSQL connection pool isolation.
        </div>
    </div>
    '''

    # Embed figures into markdown
    sec1_target = "## 1.4 Complete System Architecture Diagram"
    if sec1_target in md_text:
        md_text = md_text.replace(sec1_target, f"{sec1_target}\n\n{fig_topology_html}\n\n")

    sec2_target = "## 2.4 Components Eliminated"
    if sec2_target in md_text:
        md_text = md_text.replace(sec2_target, f"{sec2_target}\n\n{fig_pipeline_html}\n\n")

    sec4_target = "# Section 4: Frontend Architecture Deep Dive"
    if sec4_target in md_text:
        md_text = md_text.replace(sec4_target, f"{sec4_target}\n\n{fig_frontend_html}\n\n")

    sec6_target = "# Section 6: Security Architecture"
    if sec6_target in md_text:
        md_text = md_text.replace(sec6_target, f"{sec6_target}\n\n{fig_security_html}\n\n")

    print("Step 3: Rendering markdown to HTML...", flush=True)
    md = MarkdownIt(options_update={"highlight": highlight_code, "html": True}).enable("table").enable("strikethrough")

    # Format alerts
    def format_alerts(match):
        alert_type = match.group(1).upper()
        content = match.group(2).strip()
        badge_class = "alert-note"
        if alert_type in ("WARNING", "CAUTION"):
            badge_class = "alert-warning"
        elif alert_type == "IMPORTANT":
            badge_class = "alert-important"
        elif alert_type == "TIP":
            badge_class = "alert-tip"
        return f'<div class="alert-box {badge_class}"><div class="alert-title">{alert_type}</div><div class="alert-body">{content}</div></div>'

    md_text = re.sub(r'>\s*\[!(NOTE|IMPORTANT|WARNING|CAUTION|TIP)\]\s*\n((?:>.*\n?)*)', format_alerts, md_text)
    md_text = re.sub(r'<div class="alert-body">(.*?)</div>', lambda m: '<div class="alert-body">' + m.group(1).replace('> ', '') + '</div>', md_text, flags=re.DOTALL)

    body_html = md.render(md_text)

    # Pygments syntax styles
    pygments_css = HtmlFormatter().get_style_defs('.highlight')

    # Local mermaid path
    local_mermaid_script = "mermaid.min.js"

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SignalReport — Architectural Report</title>
    <script src="{local_mermaid_script}"></script>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'neutral',
            flowchart: {{ useMaxWidth: true, htmlLabels: true, curve: 'basis' }},
            themeVariables: {{
                fontFamily: 'Segoe UI, -apple-system, Roboto, sans-serif',
                primaryColor: '#eef2ff',
                primaryTextColor: '#1e293b',
                primaryBorderColor: '#6366f1',
                lineColor: '#4f46e5',
                secondaryColor: '#f0fdf4',
                tertiaryColor: '#f8fafc'
            }}
        }});
    </script>
    <style>
        @page {{
            size: A4 portrait;
            margin: 20mm 15mm 20mm 15mm;
        }}

        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1e293b;
            line-height: 1.55;
            font-size: 9.5pt;
            background: #ffffff;
            margin: 0;
            padding: 0;
        }}

        /* Cover Page */
        .cover-page {{
            page-break-after: always;
            padding: 60px 20px 40px 20px;
            border-left: 6px solid #4f46e5;
            min-height: 750px;
        }}

        .cover-badge {{
            display: inline-block;
            background: #eef2ff;
            color: #4f46e5;
            font-size: 8.5pt;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 6px 14px;
            border-radius: 4px;
            border: 1px solid #c7d2fe;
            margin-bottom: 25px;
        }}

        .cover-title {{
            font-size: 30pt;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.15;
            margin: 0 0 15px 0;
            letter-spacing: -0.5px;
        }}

        .cover-subtitle {{
            font-size: 15pt;
            color: #475569;
            font-weight: 400;
            margin: 0 0 25px 0;
            line-height: 1.4;
        }}

        .cover-divider {{
            height: 3px;
            width: 80px;
            background: #4f46e5;
            margin-bottom: 40px;
        }}

        .cover-metadata-grid {{
            display: grid;
            grid-template-columns: 140px 1fr;
            row-gap: 12px;
            column-gap: 15px;
            font-size: 9.5pt;
            background: #f8fafc;
            padding: 24px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            max-width: 520px;
            margin-bottom: 60px;
        }}

        .meta-label {{
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            font-size: 8pt;
            letter-spacing: 0.5px;
        }}

        .meta-value {{
            font-weight: 600;
            color: #0f172a;
        }}

        .cover-footer {{
            border-top: 1px solid #e2e8f0;
            padding-top: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8.5pt;
            color: #64748b;
        }}

        .confidential-tag {{
            color: #dc2626;
            font-weight: 700;
            letter-spacing: 1px;
        }}

        /* Headings */
        h1 {{
            font-size: 17pt;
            font-weight: 800;
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 8px;
            margin-top: 30px;
            margin-bottom: 14px;
            page-break-after: avoid;
            break-after: avoid;
            letter-spacing: -0.3px;
        }}

        body > h1:not(:first-of-type) {{
            page-break-before: always;
            break-before: always;
            margin-top: 0;
            padding-top: 10px;
        }}

        h2 {{
            font-size: 13pt;
            font-weight: 700;
            color: #1e293b;
            margin-top: 22px;
            margin-bottom: 10px;
            page-break-after: avoid;
            break-after: avoid;
            border-left: 3px solid #6366f1;
            padding-left: 10px;
        }}

        h3 {{
            font-size: 10.5pt;
            font-weight: 700;
            color: #334155;
            margin-top: 16px;
            margin-bottom: 8px;
            page-break-after: avoid;
            break-after: avoid;
        }}

        h4 {{
            font-size: 9.5pt;
            font-weight: 700;
            color: #475569;
            margin-top: 12px;
            margin-bottom: 6px;
            page-break-after: avoid;
            break-after: avoid;
        }}

        p {{
            margin-top: 0;
            margin-bottom: 10px;
            text-align: justify;
        }}

        ul, ol {{
            margin-top: 0;
            margin-bottom: 10px;
            padding-left: 20px;
        }}

        li {{
            margin-bottom: 4px;
        }}

        hr {{
            border: none;
            height: 1px;
            background: #e2e8f0;
            margin: 20px 0;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
            margin: 14px 0 18px 0;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            overflow: hidden;
        }}

        th {{
            background-color: #f1f5f9;
            color: #0f172a;
            font-weight: 700;
            text-align: left;
            padding: 8px 10px;
            border-bottom: 2px solid #cbd5e1;
            border-right: 1px solid #e2e8f0;
            font-size: 8pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 6px 10px;
            border-bottom: 1px solid #e2e8f0;
            border-right: 1px solid #e2e8f0;
            color: #334155;
            vertical-align: top;
        }}

        tr:nth-child(even) td {{
            background-color: #f8fafc;
        }}

        /* Code Blocks - Allowed to break gracefully across pages */
        .code-block-wrapper {{
            margin: 12px 0 16px 0;
            background: #0f172a;
            border-radius: 6px;
            border: 1px solid #1e293b;
            overflow: hidden;
        }}

        .code-lang-tag {{
            background: #1e293b;
            color: #94a3b8;
            font-size: 7pt;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 3px 10px;
            border-bottom: 1px solid #334155;
        }}

        pre {{
            margin: 0;
            padding: 10px 12px;
            overflow-x: auto;
            font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
            font-size: 7.8pt;
            line-height: 1.42;
            color: #f8fafc;
            background: #0f172a;
            white-space: pre-wrap;
            word-break: break-all;
        }}

        code {{
            font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
            font-size: 8pt;
        }}

        p code, li code, td code {{
            background: #f1f5f9;
            color: #0f172a;
            padding: 1px 4px;
            border-radius: 3px;
            border: 1px solid #e2e8f0;
            font-size: 7.8pt;
        }}

        /* Figure Cards */
        .figure-card {{
            margin: 20px 0 24px 0;
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            page-break-inside: avoid;
            break-inside: avoid;
            color: #f8fafc;
        }}

        .figure-badge {{
            display: inline-block;
            background: #312e81;
            color: #a5b4fc;
            font-size: 7pt;
            font-weight: 700;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            padding: 3px 8px;
            border-radius: 4px;
            margin-bottom: 8px;
            border: 1px solid #4338ca;
        }}

        .figure-img-wrap {{
            width: 100%;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #334155;
            background: #000;
            line-height: 0;
        }}

        .figure-img-wrap img {{
            width: 100%;
            height: auto;
            display: block;
        }}

        .figure-caption {{
            font-size: 7.8pt;
            color: #cbd5e1;
            margin-top: 8px;
            line-height: 1.45;
            padding: 0 4px;
        }}

        .figure-caption strong {{
            color: #38bdf8;
        }}

        /* Mermaid Diagrams Container */
        .mermaid-container {{
            margin: 14px 0 18px 0;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        .mermaid svg {{
            max-width: 100% !important;
            height: auto !important;
        }}

        /* Alert Boxes */
        .alert-box {{
            padding: 10px 12px;
            border-radius: 6px;
            margin: 12px 0;
            font-size: 8.5pt;
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        .alert-note {{
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            color: #1e3a8a;
        }}

        .alert-important {{
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            color: #991b1b;
        }}

        .alert-warning {{
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            color: #92400e;
        }}

        .alert-tip {{
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            color: #065f46;
        }}

        .alert-title {{
            font-weight: 700;
            font-size: 7.5pt;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 3px;
        }}

        /* Pygments Highlighting */
        {pygments_css}
        .highlight .k {{ color: #f43f5e; font-weight: bold; }}
        .highlight .kd {{ color: #f43f5e; font-weight: bold; }}
        .highlight .kn {{ color: #f43f5e; font-weight: bold; }}
        .highlight .kp {{ color: #f43f5e; font-weight: bold; }}
        .highlight .s {{ color: #34d399; }}
        .highlight .s1 {{ color: #34d399; }}
        .highlight .s2 {{ color: #34d399; }}
        .highlight .nb {{ color: #38bdf8; }}
        .highlight .nf {{ color: #60a5fa; font-weight: bold; }}
        .highlight .nc {{ color: #fbbf24; font-weight: bold; }}
        .highlight .nn {{ color: #94a3b8; }}
        .highlight .c {{ color: #64748b; font-style: italic; }}
        .highlight .c1 {{ color: #64748b; font-style: italic; }}
        .highlight .mi {{ color: #f59e0b; }}
        .highlight .mf {{ color: #f59e0b; }}
        .highlight .ow {{ color: #f43f5e; }}
        .highlight .o {{ color: #cbd5e1; }}
        .highlight .gd {{ color: #ef4444; background-color: #450a0a; }}
        .highlight .gi {{ color: #10b981; background-color: #022c22; }}
    </style>
</head>
<body>

    <!-- Cover Page -->
    <div class="cover-page">
        <div class="cover-badge">Enterprise Engineering Architecture &bull; Technical Specification</div>
        <h1 class="cover-title">SignalReport</h1>
        <div class="cover-subtitle">Enterprise AI News Analyst &mdash; Exhaustive Architectural & Implementation Report</div>
        <div class="cover-divider"></div>

        <div class="cover-metadata-grid">
            <div class="meta-label">Author:</div>
            <div class="meta-value">Antigravity Principal Systems Architect</div>

            <div class="meta-label">Project Lead:</div>
            <div class="meta-value">Shaik Firdos</div>

            <div class="meta-label">Date:</div>
            <div class="meta-value">2026-09-22</div>

            <div class="meta-label">System Version:</div>
            <div class="meta-value">1.0.0 (FastAPI + Asyncpg Lean Stack)</div>

            <div class="meta-label">Classification:</div>
            <div class="meta-value">INTERNAL &mdash; ENGINEERING REFERENCE</div>

            <div class="meta-label">Core Tech Stack:</div>
            <div class="meta-value">FastAPI, PostgreSQL 18, React 18, Vite, asyncpg</div>
        </div>

        <div class="cover-footer">
            <div>SignalReport Platform Engineering &bull; Production Architecture</div>
            <div class="confidential-tag">STRICTLY CONFIDENTIAL</div>
        </div>
    </div>

    <!-- Main Content -->
    {body_html}

</body>
</html>'''

    html_path = os.path.join(WORKSPACE_DIR, "report_rendered.html")
    print(f"Step 4: Writing rendered HTML to: {html_path}", flush=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    print("Step 5: Launching Playwright with MS Edge...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        file_url = f"file:///{html_path.replace(os.sep, '/')}"
        print(f"Navigating to: {file_url}", flush=True)
        page.goto(file_url, wait_until="load")

        print("Waiting for Mermaid SVGs to render...", flush=True)
        try:
            page.wait_for_selector(".mermaid svg", timeout=10000)
            print("Mermaid SVGs rendered successfully!", flush=True)
        except Exception as e:
            print(f"Mermaid wait notice: {e}", flush=True)

        # Brief settle time
        page.wait_for_timeout(1500)

        print(f"Printing PDF to: {OUTPUT_PDF_PATH} ...", flush=True)
        page.pdf(
            path=OUTPUT_PDF_PATH,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template='<div style="font-size: 7.5pt; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; width: 100%; text-align: right; color: #94a3b8; padding-right: 15mm;">SignalReport &mdash; Enterprise AI News Analyst &bull; Technical Architecture Report</div>',
            footer_template='<div style="font-size: 7.5pt; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; width: 100%; display: flex; justify-content: space-between; color: #94a3b8; padding: 0 15mm;"><span style="color: #dc2626; font-weight: 700; letter-spacing: 0.5px;">INTERNAL &bull; ENGINEERING REFERENCE</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>',
            margin={
                "top": "22mm",
                "bottom": "22mm",
                "left": "15mm",
                "right": "15mm"
            }
        )

        print(f"Copying PDF to artifact directory: {ARTIFACT_PDF_PATH}", flush=True)
        shutil.copyfile(OUTPUT_PDF_PATH, ARTIFACT_PDF_PATH)
        browser.close()

    size_mb = os.path.getsize(OUTPUT_PDF_PATH) / (1024 * 1024)
    print(f"PDF SUCCESS! File size: {size_mb:.2f} MB", flush=True)

if __name__ == "__main__":
    build_pdf()
