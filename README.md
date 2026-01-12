# 💰📊 Budget Manager Sync – README 🔄🏠

<img width="321" height="275" alt="image" src="https://github.com/user-attachments/assets/288b8449-4c37-426d-acc1-3d0a9270c0f3" />

## Support this project

If you find this project useful, you can support me on Ko-fi 💙

[![Buy me some debugging time on Ko-fi](https://img.shields.io/badge/%F0%9F%90%9E_Buy_me_some_debugging_time_on-Ko--fi-2ea44f?style=for-the-badge)](https://ko-fi.com/qlerup)

## ⚠️ Prerequisite: install the card first 🧩🖼️

This integration requires the **Budget Manager Card** (the Lovelace UI) to be installed and working:

[https://github.com/qlerup/budget-manager-card](https://github.com/qlerup/budget-manager-card)

> The integration exposes a **sensor** (e.g. `sensor.budget_overview`) with budget data in attributes, and a service domain `budget_manager`. The card reads the sensor and calls the services to add/update/remove items and participants. 🔌🧠

---

## 🎯 What does the “sync” part do? ✅🔄

**Budget Manager Sync** is the backend piece that makes the card actually *work* long-term. 🧠💾

It is built to **track + persist all data created through the card**, including:

* 🧾➕ Entries/transactions added via the card
* 👤📝 Names/participants created in the card
* 💸👥 Expenses per person
* 💰🧮 Total combined expenses

In other words: the card is the UI 🧩🖼️, and **Budget Manager Sync** is what stores and exposes the data in Home Assistant so your budget doesn’t disappear on reload/restart. 🔥➡️❄️✅

---

## 🧩 Card vs integration (how they work together) 🤝

* The **integration** typically exposes:

  * A **sensor** (example used by the card: `sensor.budget_overview`) 📡
  * Sensor attributes like `items` and `participants` 📋👥
  * A set of **services** under a domain named `budget_manager` 🔧

* The **Budget Manager Card** reads the sensor and calls those services to:

  * Add/update/remove items ➕✏️🗑️
  * Add/remove participants 👤➕👤➖

---

## 📡 What the card expects from the integration (contract) 📜✅

### 1) A sensor with attributes 🧠

The card expects a configured sensor entity (for example `sensor.budget_overview`) that contains:

* `attributes.items` (array) 📋
* `attributes.participants` (array) 👥

If `participants` is missing, the card will fall back to `['Christian','Yasmin']` as a UI fallback 🧯🙂, but in a real setup you want the integration to provide the real list.

### 2) Services used by the card 🔧

The card calls these services (so the integration must provide them for full functionality):

* `budget_manager.set_participants`

  * Payload: `{ names: ["Alice", "Bob", ...] }` 👥

* `budget_manager.add_item`

  * Payload: `{ name, amount, frequency, payer }` ➕🧾

* `budget_manager.update_item_by_name`

  * Payload: `{ name, new_name?, amount?, frequency?, payer? }` ✏️🔁

* `budget_manager.remove_item_by_name`

  * Payload: `{ name }` 🗑️

> 📝 Note: These names/payloads are based on what the card calls. If you customize the integration, keep the API aligned. 🤝⚙️

---

## 🧰 Installation (HACS) 🛒✨

From the integration’s README, the intended flow is:

1. Open **HACS** in Home Assistant 🏠
2. Go to **Integrations** → **⋮** → **Custom repositories** ⚙️
3. Add this repository as an **Integration** ➕📌

   * [https://github.com/qlerup/budget-manager-sync](https://github.com/qlerup/budget-manager-sync)
4. Install ✅ and restart Home Assistant 🔄🚀

> ⚠️ **Important:** Installing from HACS is not enough. After the restart, go to **Settings → Devices & Services** ("Enheder & tjenester") and **Add Integration** → **Budget Manager Sync**.

---

## ⚙️ Configuration (after HACS install) 🧩✅

After installing via HACS and restarting Home Assistant, you still need to **add the integration** in Home Assistant’s UI.

> 🇩🇰 Efter installation skal du ind i **Enheder & tjenester** (Devices & Services) og tilføje integrationen derinde — ellers dukker sensoren/services ikke op.

### 1) Add the integration in Home Assistant UI ➕

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Budget Manager Sync**
4. Click it and complete the setup flow ✅

> If you don’t see it in the list right away, make sure Home Assistant has been restarted after installing from HACS.

### 2) What gets created? 📡

When the integration is added, it will create the budget sensor the card reads, typically:

* `sensor.budget_overview`

This sensor contains:

* `attributes.items` 📋
* `attributes.participants` 👥

It will also register the services under:

* `budget_manager.*` 🔧

---

## 🧩 Use with the Lovelace Card (frontend) 🖼️➡️📡

Once the integration is installed **and** added via the UI, hook it up to the **Budget Manager Card**.

### 1) Install the card 🧩

Follow the card installation guide here:

[https://github.com/qlerup/budget-manager-card](https://github.com/qlerup/budget-manager-card)

### 2) Point the card at the integration sensor 🎯

In your Lovelace dashboard, add the card and set the sensor entity to the one created by this integration (example):

* `sensor.budget_overview`

> The card reads `items` + `participants` from the sensor attributes and calls the `budget_manager.*` services to make changes.

### 3) Using it day-to-day 🧾

* Add participants in the card 👥
* Add expenses/items in the card ➕🧾
* Edit or remove items ✏️🗑️

All changes are saved by **Budget Manager Sync**, so your data persists across reloads/restarts ✅

---

## 🧪 Quick sanity checks ✅🔍

* In **Developer Tools → States**, verify the budget sensor exists (e.g. `sensor.budget_overview`) 📡
* Check that it has `attributes.items` and `attributes.participants` 📋👥
* In **Developer Tools → Services**, verify the `budget_manager.*` services exist 🔧
* Open the browser console and confirm the card loads (you’ll see a log line like `BUDGET-MANAGER-CARD v1.0.0`) 🖥️✅

---

## 🆘 Support / Issues 🐛💡

If you hit bugs or want improvements, open an issue here:

* [https://github.com/qlerup/budget-manager-sync/issues](https://github.com/qlerup/budget-manager-sync/issues) 🧷
