from __future__ import annotations

import logging
import uuid
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION, SIGNAL_UPDATED

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load storage, expose services, forward to sensor platform."""
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.json")
    data = await store.async_load() or {"items": [], "participants": ["Christian", "Yasmin"]}

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["store"] = store
    hass.data[DOMAIN]["items"] = data.get("items", [])
    hass.data[DOMAIN]["participants"] = data.get("participants") or ["Christian", "Yasmin"]
    # sensor.py sætter hass.data[DOMAIN]["manager"]

    def _normalize(item: dict) -> dict:
        item["name"] = str(item.get("name", "")).strip()
        item["frequency"] = str(item.get("frequency", "monthly")).lower()  # monthly|quarterly|yearly
        p_raw = str(item.get("payer", "Begge")).strip()
        p_low = p_raw.lower()
        def _label_all():
            parts = hass.data[DOMAIN].get("participants") or []
            return "Begge" if len(parts) == 2 else "Alle"
        # "Begge/Alle" er en fast grupperingsmulighed uanset navneliste
        if p_low.startswith("beg") or p_low.startswith("all"):
            item["payer"] = _label_all()
        else:
            item["payer"] = p_raw
        return item

    async def _save_and_broadcast():
        await store.async_save({
            "items": hass.data[DOMAIN]["items"],
            "participants": hass.data[DOMAIN]["participants"],
        })
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    # ---------- Services ----------

    async def add_item(call: ServiceCall):
        item = _normalize({
            "id": str(uuid.uuid4()),
            "name": call.data["name"],
            "amount": float(call.data["amount"]),
            "frequency": call.data.get("frequency", "monthly"),
            "payer": call.data.get("payer", "Begge"),
        })
        hass.data[DOMAIN]["items"].append(item)
        await _save_and_broadcast()

    async def update_item(call: ServiceCall):
        """Opdater via ID (stabil måde)."""
        iid = call.data["id"]
        for it in hass.data[DOMAIN]["items"]:
            if it["id"] == iid:
                if "name" in call.data: it["name"] = call.data["name"]
                if "amount" in call.data: it["amount"] = float(call.data["amount"])
                if "frequency" in call.data: it["frequency"] = call.data["frequency"]
                if "payer" in call.data: it["payer"] = call.data["payer"]
                _normalize(it)
                await _save_and_broadcast()
                return
        _LOGGER.warning("budget_manager.update_item: item id %s not found", iid)

    async def update_item_by_name(call: ServiceCall):
        """
        Opdater via navn (case-insensitive). Opdaterer ALLE poster der matcher.
        Felter: new_name, amount, frequency, payer.
        Opdaterer også Entity Registry-navnet med det samme.
        """
        name = str(call.data["name"]).strip().lower()
        fields = {}
        if "new_name" in call.data: fields["name"] = call.data["new_name"]
        if "amount" in call.data: fields["amount"] = float(call.data["amount"])
        if "frequency" in call.data: fields["frequency"] = call.data["frequency"]
        if "payer" in call.data: fields["payer"] = call.data["payer"]

        if not fields:
            _LOGGER.warning("budget_manager.update_item_by_name: no fields to update for name=%s", name)
            return

        matched_ids = []
        for it in hass.data[DOMAIN]["items"]:
            if it["name"].strip().lower() == name:
                it.update(fields)
                _normalize(it)
                matched_ids.append(it["id"])

        if not matched_ids:
            _LOGGER.warning("budget_manager.update_item_by_name: no items matched name='%s'", name)
            return

        # Gem & broadcast (trigger sensorer til at opdatere)
        await _save_and_broadcast()

        # Opdatér også navnet i Entity Registry (så det vises i Entiteter med det samme)
        if "name" in fields:
            registry = er.async_get(hass)
            new_title = f"Budget – {fields['name']}"
            for iid in matched_ids:
                unique_id = f"budget_item_{iid}"
                entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
                if entity_id:
                    registry.async_update_entity(entity_id, name=new_title)

    async def remove_item(call: ServiceCall):
        iid = call.data["id"]
        items = hass.data[DOMAIN]["items"]
        new_items = [it for it in items if it["id"] != iid]
        if len(new_items) == len(items):
            _LOGGER.warning("budget_manager.remove_item: item id %s not found", iid)
        hass.data[DOMAIN]["items"] = new_items
        await _save_and_broadcast()

    async def remove_item_by_name(call: ServiceCall):
        """Slet ALLE poster der matcher navnet (case-insensitive)."""
        name = str(call.data["name"]).strip().lower()
        items = hass.data[DOMAIN]["items"]
        new_items = [it for it in items if it["name"].strip().lower() != name]
        removed = len(items) - len(new_items)
        if removed:
            hass.data[DOMAIN]["items"] = new_items
            _LOGGER.debug("budget_manager.remove_item_by_name: removed %d item(s) named '%s'", removed, name)
            await _save_and_broadcast()
        else:
            _LOGGER.warning("budget_manager.remove_item_by_name: no items matched name='%s'", name)

    async def clear_items(call: ServiceCall):
        hass.data[DOMAIN]["items"] = []
        await _save_and_broadcast()

    async def rebuild_entities(call: ServiceCall):
        """Tving sensor-platform til at genskabe/fjerne entiteter i forhold til items."""
        manager = hass.data[DOMAIN].get("manager")
        if manager:
            await manager.async_reconcile()

    async def set_participants(call: ServiceCall):
        """Sæt listen af deltagernavne (min. 1)."""
        raw = call.data.get("names", [])
        names = []
        if isinstance(raw, list):
            for n in raw:
                s = str(n).strip()
                if s and s.lower() not in ("begge", "alle"):
                    names.append(s)
        # dedup, bevar rækkefølge
        seen = set()
        dedup = []
        for n in names:
            if n.lower() not in seen:
                dedup.append(n)
                seen.add(n.lower())
        if not dedup:
            _LOGGER.warning("budget_manager.set_participants: at least one name is required")
            return
        hass.data[DOMAIN]["participants"] = dedup
        # Opdatér eksisterende items der har grupperingsalias (Begge/Alle) til korrekt label
        parts = dedup
        label_all = "Begge" if len(parts) == 2 else "Alle"
        for it in hass.data[DOMAIN]["items"]:
            p = str(it.get("payer", "")).lower()
            if p.startswith("beg") or p.startswith("all"):
                it["payer"] = label_all
        await _save_and_broadcast()

    # Registrér services
    hass.services.async_register(DOMAIN, "add_item", add_item)
    hass.services.async_register(DOMAIN, "update_item", update_item)
    hass.services.async_register(DOMAIN, "update_item_by_name", update_item_by_name)
    hass.services.async_register(DOMAIN, "remove_item", remove_item)
    hass.services.async_register(DOMAIN, "remove_item_by_name", remove_item_by_name)
    hass.services.async_register(DOMAIN, "clear", clear_items)
    hass.services.async_register(DOMAIN, "rebuild_entities", rebuild_entities)
    hass.services.async_register(DOMAIN, "set_participants", set_participants)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
