# LaTeX to PDF MCP Server

A Model Context Protocol (MCP) server that compiles LaTeX source code to PDF documents. This server provides a simple API for converting LaTeX strings into PDF files, with optional bibliography support.

## Features

- **LaTeX Compilation**: Compile LaTeX source code to PDF using Tectonic
- **Bibliography Support**: Automatically handle BibTeX references and citations
- **Error Checking**: Integrated ChkTeX for LaTeX syntax validation
- **HTTP API**: RESTful endpoints for PDF generation and download
- **Docker Support**: Containerized deployment for easy setup
- **MCP Integration**: Compatible with MCP clients for seamless integration

## Installation

### Using Docker (Recommended)

#### Option 1: Pull from Docker Hub

```bash
docker run -p 8000:8000 pranavgnn/latex-mcp-server:latest
```

[Docker Hub Repository](https://hub.docker.com/repository/docker/pranavgnn/latex-mcp-server/general)

#### Option 2: Build from Source

1. Clone the repository:

   ```bash
   git clone https://github.com/pranavgnn/latex-pdf-mcp.git
   cd latex-pdf-mcp
   ```

2. Build the Docker image:

   ```bash
   docker build -t latex-mcp-server .
   ```

3. Run the container:
   ```bash
   docker run -p 8000:8000 latex-mcp-server
   ```

The server will be available at `http://localhost:8000`.

### Local Installation

1. Install system dependencies:

   - Tectonic: Follow installation instructions at [tectonic-typesetting.github.io](https://tectonic-typesetting.github.io/)
   - ChkTeX: Install via your package manager (e.g., `apt install chktex` on Ubuntu)

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python app.py
   ```

## Usage

### MCP Tool

The server exposes a `compile_latex` tool that accepts:

- `latex` (required): LaTeX source code as a string
- `bibliography` (optional): BibTeX content for citations
- `filename` (optional): Custom filename for the output PDF

### HTTP API

- **POST** `/messages`: MCP protocol endpoint
- **GET** `/download/{filename}`: Download compiled PDF

### Example Usage

```python
# Example LaTeX compilation request
{
  "latex": "\\documentclass{article}\n\\begin{document}\nHello, World!\n\\end{document}",
  "filename": "hello.pdf"
}
```

For documents with citations:

```python
{
  "latex": "\\documentclass{article}\n\\addbibresource{references.bib}\n\\begin{document}\nHello \\cite{example}.\n\\printbibliography\n\\end{document}",
  "bibliography": "@article{example,\n  title={Example Paper},\n  author={Author, A.},\n  year={2023}\n}"
}
```

## Development

### Prerequisites

- Python 3.8+
- Tectonic
- ChkTeX

### Running Tests

```bash
# Add test commands here when implemented
```

### Building Docker Image

```bash
docker build -t latex-mcp-server .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Tectonic](https://tectonic-typesetting.github.io/) for LaTeX compilation
- [ChkTeX](https://www.nongnu.org/chktex/) for LaTeX validation
- [Model Context Protocol](https://modelcontextprotocol.io/) for the protocol specification
