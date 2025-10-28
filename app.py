from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
import subprocess
import tempfile
import shutil
from pathlib import Path
import base64
import uvicorn
import os
from datetime import datetime
import re
from typing import Optional


PDF_OUTPUT_DIR = Path("/tmp/latex-pdfs")
PDF_OUTPUT_DIR.mkdir(exist_ok=True)


def filter_compilation_output(output: str) -> str:
    lines = output.split('\n')
    filtered_lines = []
    
    for line in lines:
        if line.strip().startswith('note:'):
            continue
        if not line.strip():
            continue
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)


def compile_latex_string(latex_content: str, bib_content: Optional[str] = None) -> bytes:
    tmpdir = None
    chktex_output = None
    
    try:
        tmpdir = tempfile.mkdtemp()
        tmpdir_path = Path(tmpdir)
        main_tex = tmpdir_path / "main.tex"
        
        main_tex.write_text(latex_content, encoding='utf-8')
        
        if bib_content:
            bib_file = tmpdir_path / "references.bib"
            bib_file.write_text(bib_content, encoding='utf-8')
            
            latex_with_bib = latex_content
            if '\\addbibresource{' not in latex_with_bib and '\\bibliography{' not in latex_with_bib:
                preamble_match = re.search(r'(\\begin{document})', latex_with_bib)
                if preamble_match:
                    latex_with_bib = latex_with_bib[:preamble_match.start()] + f'\\addbibresource{{references.bib}}\n' + latex_with_bib[preamble_match.start():]
            
            main_tex.write_text(latex_with_bib, encoding='utf-8')
        
        try:
            chktex_result = subprocess.run(
                ["chktex", "-q", str(main_tex)],
                capture_output=True,
                text=True,
                timeout=10
            )
            chktex_output = chktex_result.stdout.strip() if chktex_result.stdout else None
        except subprocess.TimeoutExpired:
            chktex_output = "ChkTeX timeout"
        except Exception:
            pass
        
        result = subprocess.run(
            ["tectonic", str(main_tex), "--outdir", str(tmpdir_path)],
            check=True,
            capture_output=True,
            timeout=60,
            text=True
        )
        
        pdf_path = main_tex.with_suffix('.pdf')
        if not pdf_path.exists():
            raise Exception("Compilation failed: PDF not generated")
        
        pdf_content = pdf_path.read_bytes()
        return pdf_content
        
    except subprocess.TimeoutExpired:
        if chktex_output:
            raise Exception(f"ChkTeX Warnings:\n{chktex_output}\n\nCompilation timeout")
        raise Exception("Compilation timeout")
        
    except subprocess.CalledProcessError as e:
        error_parts = []
        if e.stderr:
            filtered_stderr = filter_compilation_output(e.stderr)
            if filtered_stderr:
                error_parts.append(filtered_stderr)
        if e.stdout:
            filtered_stdout = filter_compilation_output(e.stdout)
            if filtered_stdout:
                error_parts.append(filtered_stdout)
        
        compilation_error = "\n".join(error_parts) if error_parts else "Unknown compilation error"
        
        if chktex_output:
            raise Exception(f"ChkTeX Warnings:\n{chktex_output}\n\nCompilation Error:\n{compilation_error}")
        else:
            raise Exception(f"Compilation Error:\n{compilation_error}")
            
    except Exception as e:
        if chktex_output:
            raise Exception(f"ChkTeX Warnings:\n{chktex_output}\n\nError: {str(e)}")
        raise
        
    finally:
        if tmpdir and Path(tmpdir).exists():
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass


def save_pdf(pdf_bytes: bytes, filename: Optional[str] = None) -> tuple[str, str]:
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{timestamp}"
    
    if not filename.endswith(".pdf"):
        filename = f"{filename}.pdf"
    
    output_path = PDF_OUTPUT_DIR / filename
    
    if output_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{output_path.stem}_{timestamp}.pdf"
        output_path = PDF_OUTPUT_DIR / filename
    
    output_path.write_bytes(pdf_bytes)
    return str(output_path), filename


mcp_server = Server("latex-mcp-server")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="compile_latex",
            description="Compile LaTeX source code to PDF. Optionally include bibliography for documents with citations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "latex": {
                        "type": "string",
                        "description": "LaTeX source code to compile"
                    },
                    "bibliography": {
                        "type": "string",
                        "description": "BibTeX bibliography content (.bib file) - optional, only needed for documents with \\cite or \\printbibliography"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Name for the output PDF file (optional, defaults to timestamp)"
                    }
                },
                "required": ["latex"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "compile_latex":
        latex = arguments.get("latex")
        if not latex:
            return [TextContent(type="text", text="Error: Missing 'latex' parameter")]
        
        try:
            bibliography = arguments.get("bibliography")
            pdf_bytes = compile_latex_string(latex, bibliography)
            output_path, filename = save_pdf(pdf_bytes, arguments.get("filename"))
            
            bib_note = " with bibliography" if bibliography else ""
            
            return [TextContent(
                type="text",
                text=f"PDF{bib_note} compiled successfully!\n\nFile saved to: {output_path}\nSize: {len(pdf_bytes)} bytes\n\nDownload: http://localhost:4000/download/{filename}"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def download_pdf(request: Request):
    filename = request.path_params['filename']
    file_path = PDF_OUTPUT_DIR / filename
    
    if not file_path.exists():
        return JSONResponse(
            content={"status": 404, "message": "not found"},
            status_code=404
        )
    
    pdf_content = file_path.read_bytes()
    
    try:
        file_path.unlink()
    except Exception:
        pass
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


async def send_404(send):
    await send({
        'type': 'http.response.start',
        'status': 404,
        'headers': [[b'content-type', b'application/json']],
    })
    await send({
        'type': 'http.response.body',
        'body': b'{"status": 404, "message": "not found"}',
    })


sse = SseServerTransport("/messages")


async def mcp_app(scope, receive, send):
    if scope["type"] == "http":
        path = scope["path"]
        
        if path == "/sse":
            async with sse.connect_sse(scope, receive, send) as streams:
                await mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp_server.create_initialization_options()
                )
        elif path == "/messages":
            await sse.handle_post_message(scope, receive, send)
        else:
            await send_404(send)


app = Starlette(
    routes=[
        Route("/download/{filename}", endpoint=download_pdf),
        Mount("/", app=mcp_app)
    ]
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
