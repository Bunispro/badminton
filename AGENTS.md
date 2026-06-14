# Instructions for Coding Agents

This project contains a Badminton Rating and Leaderboard Application (Elo & WHR models) along with a rich Next.js client interface.

To ensure consistency in styling, data rendering, and backend integrations, all agents must read and adhere to the guidelines documented here.

## 🎨 1. Front-end Design & Style Guidelines

Before making any UI or styling changes, you **must** read:
1. **[Design System Guidelines](file:///d:/badminton/web/frontend_new/docs/design_system.md)**: Governs typography, color palettes, standard grids, Recharts styles, and responsive cards.
2. **[Rank-Based Player Profile Styles](file:///d:/badminton/docs/player_profile_styles.md)**: Details custom effects (Ruby, Cobalt, Emerald, etc.) applied to names depending on their global ranking.

### Critical Rules
- **No hardcoded backend URLs/ports**: Always import and use `API_BASE_URL` from `@/lib/api` in frontend code.
- **Name Wrapping**: Do not truncate or clip long player names. Use `break-words whitespace-normal line-clamp-2` or similar styles to wrap names.
- **Activity Threshold**: Inactivity is defined as no matches played in the last **8 months (240 days)**. Inactive players must be hidden from all seasonal leaderboard views.

---

## 🧮 2. Backend & Rating Engines

- **SQLite Database Path**:
  - Raw matches and metadata: `d:\badminton\bwf_data_2008-now__v1.sqlite`
  - Rating engines output: `d:\badminton\elo_ratings.sqlite`
- **Port**: The backend API server runs on port **8001** (e.g. `uvicorn main:app --port 8001 --reload`).
- **Engines**: Matches are rated using custom Elo calculations ([elo_engine_1_0.py](file:///d:/badminton/elo_engine_1_0.py)) and Whole History Rating (WHR) calculations ([run_whr.py](file:///d:/badminton/run_whr.py)).
