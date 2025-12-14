from __future__ import annotations

import logging
from typing import Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, SIGNAL_UPDATED

_LOGGER = logging.getLogger(__name__)

FREQ_FACTORS = {"monthly": 1.0, "quarterly": 1 / 3, "yearly": 1 / 12}


def monthly(amount: float, frequency: str) -> float:
    return float(amount) * FREQ_FACTORS.get((frequency or "monthly").lower(), 1.0)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    manager = BudgetEntityManager(hass, async_add_entities, entry)
    hass.data[DOMAIN]["manager"] = manager
    await manager.async_load_initial()
    manager.attach_listeners()


class BudgetEntityManager:
    """Holder styr på dynamiske entiteter og rydder forældreløse op."""

    def __init__(
        self, hass: HomeAssistant, add_entities: AddEntitiesCallback, entry: ConfigEntry
    ):
        self.hass = hass
        self.add_entities = add_entities
        self.entry_id = entry.entry_id
        self.item_entities: Dict[str, BudgetItemSensor] = {}
        self.overview = BudgetOverviewSensor(hass)
        self._unsub = None

    async def async_load_initial(self):
        # Overview
        self.add_entities([self.overview], True)
        # Eksisterende items
        items = self.hass.data[DOMAIN]["items"]
        initial = []
        for it in items:
            ent = BudgetItemSensor(self.hass, it["id"])
            self.item_entities[it["id"]] = ent
            initial.append(ent)
        if initial:
            self.add_entities(initial, True)

    def attach_listeners(self):
        if self._unsub:
            return
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_UPDATED, self._on_data_changed
        )

    async def _on_data_changed(self):
        await self.async_reconcile()
        # Opdatér overview + alle items (inkl. navn)
        self.overview.async_write_ha_state()
        for ent in self.item_entities.values():
            await ent._refresh()   # sørger for både navn og state

    async def async_reconcile(self):
        """Sørg for at der findes én entitet pr. item – og fjern forældreløse (også i registry)."""
        items = self.hass.data[DOMAIN]["items"]
        current_ids = {it["id"] for it in items}

        # Kørende entiteter
        runtime_ids = set(self.item_entities.keys())

        # Registry-entries for denne config entry
        registry = er.async_get(self.hass)
        reg_entries = er.async_entries_for_config_entry(registry, self.entry_id)
        reg_item_ids = set()
        for e in reg_entries:
            if e.platform == "sensor" and e.unique_id.startswith("budget_item_"):
                reg_item_ids.add(e.unique_id.replace("budget_item_", ""))

        # Tilføj nye
        to_add = current_ids - runtime_ids
        if to_add:
            new = []
            for iid in to_add:
                ent = BudgetItemSensor(self.hass, iid)
                self.item_entities[iid] = ent
                new.append(ent)
            self.add_entities(new, True)

        # Fjern forældreløse (runtime + registry)
        to_remove = (runtime_ids | reg_item_ids) - current_ids
        if to_remove:
            for iid in to_remove:
                ent = self.item_entities.pop(iid, None)
                if ent:
                    await ent.async_remove()
                unique_id = f"budget_item_{iid}"
                for e in reg_entries:
                    if e.unique_id == unique_id:
                        registry.async_remove(e.entity_id)


class BudgetOverviewSensor(SensorEntity):
    _attr_name = "Budget Overview"
    _attr_icon = "mdi:calculator-variant"
    _attr_native_unit_of_measurement = "DKK/month"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._attr_unique_id = "budget_manager_overview"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "budget_manager")},
            name="Budget Manager",
            manufacturer="Custom",
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._refresh)
        )
        await self._refresh()

    async def _refresh(self):
        self.async_write_ha_state()

    @property
    def native_value(self):
        total = 0.0
        for it in self.hass.data[DOMAIN]["items"]:
            total += monthly(it["amount"], it["frequency"])
        return round(total, 2)

    @property
    def extra_state_attributes(self):
        items_attr = []
        participants = self.hass.data[DOMAIN].get("participants") or ["Christian", "Yasmin"]
        totals: Dict[str, float] = {p: 0.0 for p in participants}

        for it in self.hass.data[DOMAIN]["items"]:
            m = monthly(it["amount"], it["frequency"])
            payer = str(it.get("payer", "Begge"))
            transfers = {p: 0.0 for p in participants}

            if payer.lower() in ("begge", "alle") or len(participants) == 0:
                share = m / max(1, len(participants))
                for p in participants:
                    transfers[p] = share
            else:
                # match payer case-insensitivt mod deltagere, ellers fallback til Begge
                match = next((p for p in participants if p.lower() == payer.lower()), None)
                if match:
                    transfers[match] = m
                else:
                    share = m / max(1, len(participants))
                    for p in participants:
                        transfers[p] = share

            # akkumuler totals
            for p in participants:
                totals[p] += transfers[p]

            items_attr.append(
                {
                    "id": it["id"],
                    "name": it["name"],
                    "amount": round(float(it["amount"]), 2),
                    "frequency": it["frequency"],
                    "payer": payer,
                    "monthly": round(m, 2),
                    "transfers": {p: round(transfers[p], 2) for p in participants},
                }
            )

        return {
            "participants": participants,
            "items": items_attr,
            "totals": {p: round(totals[p], 2) for p in participants},
        }


class BudgetItemSensor(SensorEntity):
    """Én entitet per budgetpost (state = månedlig beløb)."""

    _attr_icon = "mdi:cash"
    _attr_native_unit_of_measurement = "DKK/month"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, item_id: str):
        self.hass = hass
        self._item_id = item_id
        self._attr_unique_id = f"budget_item_{item_id}"
        # Sæt et startnavn (skiftes igen i _refresh)
        it = self._item()
        self._attr_name = f"Budget – {it['name']}" if it else "Budget – (ukendt)"

    def _item(self) -> Optional[dict]:
        for it in self.hass.data[DOMAIN]["items"]:
            if it["id"] == self._item_id:
                return it
        return None

    async def async_added_to_hass(self):
        # Lyt til ændringer og opdater både navn og state ved hver ændring
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._refresh)
        )
        await self._refresh()

    async def _refresh(self):
        it = self._item()
        # Opdatér friendly name dynamisk
        self._attr_name = f"Budget – {it['name']}" if it else "Budget – (slettet)"
        self.async_write_ha_state()

    @property
    def native_value(self):
        it = self._item()
        if not it:
            return None
        m = monthly(float(it["amount"]), it["frequency"])
        return round(m, 2)

    @property
    def extra_state_attributes(self):
        it = self._item()
        if not it:
            return None
        m = monthly(float(it["amount"]), it["frequency"])
        payer = str(it.get("payer", "Begge"))
        participants = self.hass.data[DOMAIN].get("participants") or ["Christian", "Yasmin"]
        transfers = {p: 0.0 for p in participants}

        if payer == "Begge" or len(participants) == 0:
            share = m / max(1, len(participants))
            for p in participants:
                transfers[p] = share
        else:
            match = next((p for p in participants if p.lower() == payer.lower()), None)
            if match:
                transfers[match] = m
            else:
                share = m / max(1, len(participants))
                for p in participants:
                    transfers[p] = share

        return {
            "id": it["id"],
            "name": it["name"],
            "amount": round(float(it["amount"]), 2),
            "frequency": it["frequency"],
            "payer": payer,
            "monthly": round(m, 2),
            "transfers": {p: round(transfers[p], 2) for p in participants},
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "budget_manager")},
            name="Budget Manager",
            manufacturer="Custom",
        )
