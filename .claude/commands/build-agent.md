Read the full CLAUDE.md file. It contains all the detailed instructions.

Execute the AgentKit onboarding flow following the 5 phases IN ORDER:

PHASE 1 — Welcome and environment verification
- Show the welcome message
- Verify Python >= 3.11
- Create the necessary folders (agent/, agent/providers/, config/, knowledge/, tests/)
- Generate requirements.txt and install dependencies
- Create base .env

PHASE 2 — Business interview
- Ask the 10 questions ONE BY ONE
- Wait for a response before continuing to the next one
- QUESTION 9: the user chooses their WhatsApp provider (Meta/Twilio)
- QUESTION 10: ask for the specific credentials of the chosen provider
- Save all responses for Phase 3

PHASE 3 — Agent generation
- Generate config/business.yaml with business data
- Generate config/prompts.yaml with a powerful and specific system prompt
- If there are files in /knowledge, read them and incorporate them into the prompt
- Generate agent/providers/ with the chosen provider (base.py + __init__.py + adapter)
- Generate agent/main.py (FastAPI + provider-agnostic webhook)
- Generate agent/brain.py (Claude API)
- Generate agent/memory.py (SQLite + history)
- Generate agent/tools.py (tools based on use case)
- Generate tests/test_local.py (chat simulator)
- Generate Dockerfile and docker-compose.yml
- Configure .env with WHATSAPP_PROVIDER and the user's API keys

PHASE 4 — Local testing
- Run python tests/test_local.py
- The user chats with their agent in the terminal
- If adjustments are needed, modify prompts.yaml and repeat
- Do not advance without user approval

PHASE 5 — Deploy to Railway
- Only if the user wants to
- Docker build + Railway instructions
- Provider-specific webhook configuration

RULES:
- Always speak in English
- One question at a time
- Never hardcode API keys
- Do not advance phases without confirmation
- The agent must work before discussing deploy
- Generate ONLY the adapter for the chosen provider (not all of them)
