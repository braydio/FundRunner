# 🛠 Development Notes – Ticker Integration + Unified Status Display

📅 Date: 2025-05-20  
📁 Repo: FundRunner  
🧑‍💻 Author: Arch Linux Assistant

---

## ✅ Objective

Streamline user experience by consolidating live portfolio visibility and account insights into two enhanced views on launch.

---

## 🧭 Plan Summary

1. **Default Launch View (Live Dashboard)**

   - Auto-render on startup.
   - Shows:
     - Current datetime
     - Portfolio holdings:
       - Symbol
       - Quantity
       - Avg Entry
       - Current Price
       - $ P/L (computed)
   - Option to launch `ticker` terminal tool from this view to monitor in real-time.

2. **Account Overview Screen**

   - Separate from launch screen.
   - Shows:
     - Cash Balance
     - Buying Power
     - Equity
     - Portfolio Value
     - Order History (optional)
     - Open Orders summary

3. **Main Menu Redesign**
   - Minimize user-facing options.
   - Reduce clutter by nesting features into composite views.
   - Add one reserved scaffolded utility feature for future expansion.

---

## 🔗 Ticker Integration

- Launchable via submenu or hotkey from portfolio screen.
- Pull symbols from:
  - Current positions (`PortfolioManager.view_positions`)
  - All saved watchlists (`WatchlistManager.list_watchlists`)
- CLI call via `subprocess.run(["ticker", "-s", ...])`
- Add safety check if `ticker` is not found (fallback message).

---

## 🧪 Dev Tasks

- [x] Prototype launch dashboard method
- [x] Migrate account balance display from legacy
- [x] Patch ticker runner utility
- [ ] Nest order viewing inside account info
- [ ] Clean up unused menu options
- [ ] Add placeholder for future analytics utility
