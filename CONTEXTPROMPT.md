I want to learning how to set up an RL environment and train LLMs in the RL environment. I want to interview for a RL env comapny (fleet ai), where they need research scientists to help them create better RL envs for the fronrtier model companies to train on. I think the things I am most interested in is getting really good to at spinning up envs where I cna test changes to reward functions (specified be me) and see how they affect training dynamics of RL for an LLM. I am familiar wiht the basics of RL envs, GRPO for LLMs, etc., but wnat you to help me get fast at the use of RL envs. Maybe we can use the resources from the open source RL envs provided by prime intellect online. Do research nd find the github links so we can study and replicate the way they think about RL env seutp, and use that understanding to help me test different reward functions in a simplified RL env swtting (single turn, etc.)

## Website for Showing Experiment Results (Muon vs Adam)

### Goal
Build a website/shareable link that shows the results of Muon vs Adam experiments with explanations. Should be easy for others to click and view, with a GitHub repo containing the code to reproduce experiments.

### Approach Options

#### Option 1: Streamlit (recommended for interactive results)
- Write a Python script with plots, tables, explanations
- Push to GitHub, connect to Streamlit Cloud for a free shareable link
- Good for: interactive plots, filtering, comparing runs

#### Option 2: GitHub Pages (recommended for static results)
- Export plots as HTML (Plotly), write explanations in Markdown
- Enable GitHub Pages in repo settings
- Free link: `yourusername.github.io/repo-name`
- Good for: polished static presentation, no server needed

### Full Stack Basics Reference

**Frontend:** Streamlit (fastest for ML demos, pure Python), Next.js (production app), Static HTML + Plotly (simplest)

**Backend (if needed later):** FastAPI (Python, async, auto-docs). For a demo site showing experiment results, likely don't need a separate backend.

**Database (if needed later):** SQLite (zero setup), PostgreSQL (at scale). Can also just read from W&B API or CSV/JSON files directly.

**Deployment:** Streamlit Cloud (free, zero config), GitHub Pages (free, static only), Railway/Render (free tier, backend + DB)

**Key Concepts:**
- **Redis** — in-memory cache for fast lookups
- **Queue (Celery/RQ)** — background task processing (e.g., "run experiment" without freezing UI)

### Next Steps
1. Gather experiment results (plots, metrics, configs) for Muon vs Adam
2. Decide on Streamlit vs GitHub Pages
3. Build the site
4. Deploy and get a shareable link
