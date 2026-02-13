# Django AG-UI Playground Example

A self-contained Django application demonstrating the AG-UI protocol integration with a beautiful React chat playground.

## Features

- **Framework Integrations**: LangGraph, LlamaIndex, Agno
- **Beautiful UI**: React + Tailwind CSS + shadcn/ui components
- **Theme Support**: Light/Dark/System mode
- **Streaming**: Real-time SSE streaming for AI responses
- **Tool Calls**: Display AI tool invocations and results
- **Responsive**: Mobile-first design

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key (or Azure OpenAI)

### 1. Clone and Install Dependencies

```bash
cd examples/playground

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Environment

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
# Edit .env and set your API keys
```

### 3. Run Development Server

**Option A: Run both servers manually**

```bash
# Terminal 1: Run Django
python manage.py runserver

# Terminal 2: Run Vite dev server
cd frontend && npm run dev
```

**Option B: Run with foreman (recommended)**

```bash
# Install foreman
pip install foreman

# Run both servers
foreman start
```

Then visit: http://localhost:8000

### 4. Run Production Build

```bash
# Build frontend bundle
cd frontend
npm run build
cd ..

# Collect static files
python manage.py collectstatic

# Run Django in production mode
DEBUG=False python manage.py runserver
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | - |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | - |
| `AZURE_OPENAI_DEPLOYMENT` | Azure deployment name | gpt-4o |
| `DEFAULT_LLM_PROVIDER` | Default LLM (openai/azure_openai) | openai |
| `DEFAULT_MODEL` | Default model | gpt-4o |
| `AGUI_USE_DB_STORAGE` | Use database for conversations | false |
| `DJANGO_SECRET_KEY` | Django secret key | dev-key |

## Project Structure

```
playground/
├── frontend/                 # Vite + React application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/            # Utilities and API client
│   │   ├── App.tsx         # Main app component
│   │   └── main.tsx        # Entry point
│   ├── public/             # Static assets
│   ├── package.json        # Frontend dependencies
│   ├── vite.config.ts      # Vite configuration
│   └── tsconfig.json       # TypeScript config
├── templates/              # Django templates
├── example_app/            # Django application
│   ├── settings.py
│   ├── urls.py
│   └── playground/        # Playground views
├── manage.py
├── pyproject.toml         # Python dependencies
├── Procfile               # Foreman configuration
├── .env.example           # Environment template
└── README.md
```

## Available Agents

The playground comes with three pre-configured agents:

- **langgraph-assistant**: LangGraph-based assistant
- **llamaindex-assistant**: LlamaIndex-based assistant  
- **agno-assistant**: Agno-based assistant

Configure agents in `settings.py` under `AGUI_AGENTS`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/` | GET | List available agents |
| `/api/agents/<name>/` | POST | Run agent (streaming) |
| `/api/playground/config/` | GET | Playground configuration |
| `/api/playground/threads/` | GET/POST | List/create conversations |
| `/api/playground/threads/<id>/` | GET/DELETE | Get/delete conversation |

## Troubleshooting

### Vite not loading in development

Make sure Vite dev server is running on port 5173:
```bash
cd frontend && npm run dev
```

### Static files not loading in production

Run collectstatic:
```bash
python manage.py collectstatic
```

### Database errors

If using DB storage, run migrations:
```bash
python manage.py migrate
```

## License

MIT
