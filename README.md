# Curio - Your Personalized News Aggregator

<div align="center">

**AI-powered RSS feed aggregator with newspaper-style presentation**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql)](https://www.postgresql.org/)

</div>

## Overview

Curio is a self-hosted, personalized news aggregator that fetches content from your favorite RSS feeds and uses AI to select and condense articles based on your interests. With a beautiful newspaper-inspired interface, Curio brings you only the news that matters to you.

### Key Features

- 📰 **Newspaper-Style UI** - Beautiful, classic newspaper layout for comfortable reading
- 🤖 **AI-Powered Curation** - Uses LLM to select and summarize articles based on your preferences
- 📡 **RSS Feed Management** - Add and organize multiple RSS feeds
- 🏷️ **Category Organization** - Organize feeds into custom categories (rubriques)
- 🐳 **Easy Deployment** - Docker container ready for Unraid, Home Assistant, and other platforms
- 🔄 **Automatic Updates** - Background scheduler fetches new content automatically
- 💾 **PostgreSQL Database** - Reliable data storage with full history
- ⚙️ **Customizable** - Configure your interests and AI behavior through settings

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (for AI features)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/curio.git
   cd curio
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and add your configuration:**
   ```env
   # Required: Add your OpenAI API key
   OPENAI_API_KEY=sk-your-api-key-here

   # Optional: Customize these settings
   POSTGRES_PASSWORD=your-secure-password
   SECRET_KEY=your-secret-key
   RSS_FETCH_INTERVAL=60
   ```

4. **Start the application:**
   ```bash
   docker-compose up -d
   ```

5. **Access Curio:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### First Time Setup

1. Open http://localhost:3000/settings
2. Go to **AI Settings** tab and configure your interests
3. Go to **Categories** tab and create some categories (e.g., Technology, Science, Business)
4. Go to **RSS Feeds** tab and add your favorite feeds
5. Click the **Refresh** button in the header to fetch articles
6. Process articles with AI using the **Process New Articles** button in AI Settings

## Development

### Using DevContainer (Recommended)

This project includes a complete devcontainer setup for VSCode:

1. Install [VSCode](https://code.visualstudio.com/) and [Docker](https://www.docker.com/)
2. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. Open the project in VSCode
4. Click "Reopen in Container" when prompted
5. The development environment will be automatically configured

### Manual Development Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up database
export DATABASE_URL="postgresql://curio:curio@localhost:5432/curio"
alembic upgrade head

# Run development server
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Architecture

### Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS
- **Database**: PostgreSQL 16
- **LLM**: OpenAI API (GPT-4)
- **RSS Parser**: feedparser
- **Scheduler**: APScheduler

### Project Structure

```
curio/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Configuration and database
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic (RSS, LLM, scheduler)
│   │   └── main.py       # FastAPI application
│   ├── alembic/          # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API client
│   │   └── types.ts      # TypeScript types
│   └── package.json
├── .devcontainer/        # Development container config
├── docker-compose.yml    # Production deployment
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `LLM_MODEL` | OpenAI model to use | `gpt-4-turbo-preview` |
| `POSTGRES_PASSWORD` | Database password | `curio` |
| `SECRET_KEY` | App secret key | `change-me-in-production` |
| `RSS_FETCH_INTERVAL` | Minutes between feed updates | `60` |
| `BACKEND_PORT` | Backend port | `8000` |
| `FRONTEND_PORT` | Frontend port | `3000` |

### AI Prompt Customization

Configure your interests in the **Settings > AI Settings** page. Example:

```
I'm interested in:
- Artificial Intelligence and Machine Learning developments
- Climate change and environmental news
- Space exploration and astronomy
- Cybersecurity and privacy
- Open source software projects

Please prioritize:
- In-depth technical articles over news headlines
- Research papers and scientific discoveries
- Long-form investigative journalism

Avoid:
- Celebrity gossip
- Sports news
- Opinion pieces without data
```

## Deployment

### Docker Compose (Recommended)

The easiest way to deploy Curio:

```bash
docker-compose up -d
```

### Unraid

1. Go to the **Docker** tab
2. Click **Add Container**
3. Use the template or configure manually:
   - Repository: `your-registry/curio`
   - Network Type: `bridge`
   - Add port mappings: `3000` and `8000`
   - Add volume for PostgreSQL data
   - Add environment variables from `.env.example`

### Home Assistant Add-on

Create `config.json` for Home Assistant:

```json
{
  "name": "Curio News Aggregator",
  "version": "1.0.0",
  "slug": "curio",
  "description": "AI-powered personalized news aggregator",
  "arch": ["amd64", "armv7", "aarch64"],
  "startup": "application",
  "boot": "auto",
  "ports": {
    "3000/tcp": 3000,
    "8000/tcp": 8000
  },
  "environment": {
    "OPENAI_API_KEY": ""
  }
}
```

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

### Key Endpoints

- `GET /api/articles/` - Get articles with filters
- `POST /api/feeds/` - Add new RSS feed
- `GET /api/categories/` - Get all categories
- `POST /api/actions/fetch-feeds` - Manually trigger feed fetch
- `POST /api/actions/process-articles` - Process articles with AI
- `GET /api/settings/` - Get user settings

## Troubleshooting

### Articles not appearing

1. Check that feeds are added in Settings
2. Click the Refresh button to fetch feeds
3. Go to Settings > AI Settings and click "Process New Articles"
4. Check backend logs: `docker-compose logs backend`

### AI processing not working

1. Verify `OPENAI_API_KEY` is set correctly in `.env`
2. Check you have API credits available
3. Verify your AI preferences are configured in Settings
4. Check backend logs for API errors

### Database issues

```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Run migrations manually
docker-compose exec backend alembic upgrade head
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by classic newspaper design
- Built with modern web technologies
- Powered by OpenAI for content curation

---

**Note**: This project requires an OpenAI API key. API usage will incur costs based on your usage. Monitor your API usage at https://platform.openai.com/usage
