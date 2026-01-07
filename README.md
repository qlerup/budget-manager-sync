# 💰📊 Budget Manager Sync – README 🔄🏠

<img width="336" height="282" alt="image" src="https://github.com/user-attachments/assets/c8316146-ae0a-44e9-b857-da698b0c10c6" />


## ⚠️ Prerequisite: install the Lovelace card too 🧩🖼️

This integration is designed to work together with the **Budget Manager Card** (the frontend UI). Install the card as well:

https://github.com/qlerup/budget-manager-card

---

## 🎯 What does the “sync” part do? ✅🔄

**Budget Manager Sync** is the backend piece that makes the card actually *work* long-term. 🧠💾

It is built to **track + persist all data created through the card**, including:

- 🧾➕ Entries/transactions added via the card
- 👤📝 Names/participants created in the card
- 💸👥 Expenses per person
- 💰🧮 Total combined expenses

In other words: the card is the UI 🧩🖼️, and **Budget Manager Sync** is what stores and exposes the data in Home Assistant so your budget doesn’t disappear on reload/restart. 🔥➡️❄️✅

---

## 🧩 Card vs integration (how they work together) 🤝

- The **integration** typically exposes:
  - A **sensor** (example used by the card: `sensor.budget_overview`) 📡
  - Sensor attributes like `items` and `participants` 📋👥
  - A set of **services** under a domain named `budget_manager` 🔧

- The **Budget Manager Card** reads the sensor and calls those services to:
  - Add/update/remove items ➕✏️🗑️
  - Add/remove participants 👤➕👤➖

---

## 📡 What the card expects from the integration (contract) 📜✅

### 1) A sensor with attributes 🧠
The card expects a configured sensor entity (for example `sensor.budget_overview`) that contains:

- `attributes.items` (array) 📋
- `attributes.participants` (array) 👥

If `participants` is missing, the card will fall back to `['Christian','Yasmin']` as a UI fallback 🧯🙂, but in a real setup you want the integration to provide the real list.

### 2) Services used by the card 🔧
The card calls these services (so the integration must provide them for full functionality):

- `budget_manager.set_participants`
  - Payload: `{ names: ["Alice", "Bob", ...] }` 👥

- `budget_manager.add_item`
  - Payload: `{ name, amount, frequency, payer }` ➕🧾

- `budget_manager.update_item_by_name`
  - Payload: `{ name, new_name?, amount?, frequency?, payer? }` ✏️🔁

- `budget_manager.remove_item_by_name`
  - Payload: `{ name }` 🗑️

> 📝 Note: These names/payloads are based on what the card calls. If you customize the integration, keep the API aligned. 🤝⚙️

---

## 🧰 Installation (HACS) 🛒✨

From the integration’s README, the intended flow is:

1. Open **HACS** in Home Assistant 🏠
2. Go to **Integrations** → **⋮** → **Custom repositories** ⚙️
3. Add this repository as an **Integration** ➕📌
   - https://github.com/qlerup/budget-manager-sync
4. Install ✅ and restart Home Assistant 🔄🚀

After this, install the **Budget Manager Card** (the frontend) and point it at the integration’s sensor. 🧩➡️📡

---

## 🧪 Quick sanity checks ✅🔍

- In **Developer Tools → States**, verify the budget sensor exists (e.g. `sensor.budget_overview`) 📡
- Check that it has `attributes.items` and `attributes.participants` 📋👥
- In **Developer Tools → Services**, verify the `budget_manager.*` services exist 🔧
- Open the browser console and confirm the card loads (you’ll see a log line like `BUDGET-MANAGER-CARD v1.0.0`) 🖥️✅

---

## 🆘 Support / Issues 🐛💡

If you hit bugs or want improvements, open an issue here:

- https://github.com/qlerup/budget-manager-sync/issues 🧷
