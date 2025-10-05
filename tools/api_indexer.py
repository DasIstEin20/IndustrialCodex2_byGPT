#!/usr/bin/env python3
"""API Inventory indexer for IndustrialCodex2_byGPT.

Scans Java source and resources (or a provided jar) to infer referenced
registries, capabilities, networking constructs, and assorted API affordances.
Outputs a narrative overview, machine-readable indices, and helper artifacts in
an `inventory/` directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
import zipfile


PACKAGE_RE = re.compile(r"^\s*package\s+([\w\.]+);", re.MULTILINE)
CLASS_RE = re.compile(r"^\s*(?:public|protected|private)?(?:\s+(?:static|abstract|final))*\s*(?:class|interface|enum)\s+(\w+)", re.MULTILINE)
DEFERRED_RE = re.compile(r"DeferredRegister<([^>]+)>\s+(\w+)")
REGISTER_CALL_RE = re.compile(r'(\w+)\.register\(\s*"([^"]+)"')
SUPPLIER_NEW_RE = re.compile(r'register\(\s*"([^"]+)"\s*,\s*\(\s*\)\s*->\s*new\s+([\w\.]+)')
SUPPLIER_REF_RE = re.compile(r'register\(\s*"([^"]+)"\s*,\s*([\w\.]+)::new')
RESOURCE_LOCATION_RE = re.compile(r'new\s+ResourceLocation\(([^\)]+)\)')
CAPABILITY_RE = re.compile(r"ForgeCapabilities\.([A-Z_]+)")
ATTACH_EVENT_RE = re.compile(r"AttachCapabilitiesEvent<([^>]+)>")
EVENTBUS_RE = re.compile(r"@Mod\.EventBusSubscriber\(([^)]*)\)")
SUBSCRIBE_EVENT_RE = re.compile(r"@SubscribeEvent")
SIMPLE_CHANNEL_RE = re.compile(r'new\s+SimpleChannel\(([^)]*)\)')
REGISTER_MESSAGE_RE = re.compile(r'registerMessage\(([^)]*)\)')
PROTOCOL_VERSION_RE = re.compile(r'PROTOCOL_VERSION\s*=\s*"([^"]+)"')
CONFIG_DEFINE_RE = re.compile(r'\.define(?:InRange|List)?\(\s*"([^"]+)"\s*,\s*([^,\)]+)(?:,\s*([^\)]+))?')
MULTIBLOCK_KEYWORDS = ("multiblock", "structure", "blueprint", "plan", "planner", "pattern", "reactor", "turbine", "controller", "casing", "hatch", "port")
CABLE_KEYWORDS = ("cable", "wire", "conduit")
REACTOR_KEYWORDS = ("reactor", "turbine", "core", "fuel")
MENU_HINTS = re.compile(r"MenuType|AbstractContainerMenu|Menu")
ENERGY_HINTS = re.compile(r"ForgeCapabilities\.ENERGY|IEnergyStorage|Energy")

REGISTRY_CATEGORY_HINTS = {
    "Block": "blocks",
    "Item": "items",
    "BlockEntity": "block_entities",
    "BlockEntityType": "block_entities",
    "EntityType": "entities",
    "MenuType": "menus",
    "ContainerType": "menus",
    "FluidType": "fluids",
    "Fluid": "fluids",
    "FlowingFluid": "fluids",
    "RecipeSerializer": "recipes",
    "SoundEvent": "sounds",
}


@dataclass
class RegistryEntry:
    category: str
    identifier: str
    class_name: Optional[str] = None
    source: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def to_json(self, modid: str) -> Dict[str, str]:
        id_value = self.identifier
        if modid and ":" not in id_value:
            id_value = f"{modid}:{id_value}"
        return {
            "id": id_value,
            "class": self.class_name or "",
            "source": self.source or "",
            "notes": "; ".join(sorted(set(self.notes))) if self.notes else "",
        }

    def to_csv_row(self, modid: str) -> List[str]:
        id_value = self.identifier
        if modid and ":" not in id_value:
            id_value = f"{modid}:{id_value}"
        return [self.category, id_value, self.class_name or "", self.source or "", "; ".join(sorted(set(self.notes))) if self.notes else ""]


@dataclass
class CapabilityEntry:
    key: str
    providers: Set[str] = field(default_factory=set)
    attach_points: Set[str] = field(default_factory=set)
    notes: Set[str] = field(default_factory=set)

    def to_json(self) -> Dict[str, str]:
        return {
            "key": self.key,
            "providers": sorted(self.providers),
            "attach_points": sorted(self.attach_points),
            "notes": "; ".join(sorted(self.notes)) if self.notes else "",
        }

    def to_csv_rows(self) -> List[List[str]]:
        note = "; ".join(sorted(self.notes)) if self.notes else ""
        provider = ", ".join(sorted(self.providers)) if self.providers else ""
        attach = ", ".join(sorted(self.attach_points)) if self.attach_points else ""
        return [["capability", self.key, provider, attach, note]]


@dataclass
class ConfigEntry:
    scope: str
    key: str
    default: str
    value_range: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def to_json(self) -> Dict[str, str]:
        return {
            "path": self.scope,
            "key": self.key,
            "default": self.default,
            "range": self.value_range or "",
            "notes": "; ".join(sorted(set(self.notes))) if self.notes else "",
        }

    def to_csv_row(self) -> List[str]:
        return ["config", f"{self.scope}:{self.key}", "", "", "; ".join(sorted(set(self.notes))) if self.notes else ""]


@dataclass
class PacketEntry:
    class_name: str
    direction: str = "both"
    notes: List[str] = field(default_factory=list)

    def to_json(self) -> Dict[str, str]:
        return {
            "class": self.class_name,
            "dir": self.direction,
            "notes": "; ".join(sorted(set(self.notes))) if self.notes else "",
        }


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")
    except Exception as exc:
        print(f"Failed to read {path}: {exc}", file=sys.stderr)
        return ""


class APIIndexer:
    def __init__(self, src_paths: Iterable[Path], res_paths: Iterable[Path], jar_path: Optional[Path], out_dir: Path) -> None:
        self.src_paths = [p for p in src_paths if p.exists()]
        self.res_paths = [p for p in res_paths if p.exists()]
        self.jar_path = jar_path if jar_path and jar_path.exists() else None
        self.out_dir = out_dir

        self.modid: str = ""
        self.mod_version: str = ""
        self.packages: Set[str] = set()
        self.registry_entries: Dict[Tuple[str, str], RegistryEntry] = {}
        self.capabilities: Dict[str, CapabilityEntry] = {}
        self.multiblocks: Dict[str, Dict[str, object]] = {}
        self.reactors: Dict[str, Dict[str, object]] = {}
        self.cables: Dict[str, Dict[str, object]] = {}
        self.network_channel: Optional[str] = None
        self.network_protocol: Optional[str] = None
        self.packet_entries: Dict[str, PacketEntry] = {}
        self.config_entries: Dict[Tuple[str, str], ConfigEntry] = {}
        self.events: Set[Tuple[str, str, str]] = set()
        self.tags: Set[Tuple[str, str]] = set()
        self.file_capabilities: Dict[Path, Set[str]] = defaultdict(set)
        self.file_menu_hints: Dict[Path, bool] = defaultdict(bool)
        self.file_energy_hints: Dict[Path, bool] = defaultdict(bool)
        self.file_multiblock_hint: Dict[Path, Set[str]] = defaultdict(set)

    # region: scanning helpers
    def scan(self) -> None:
        if self.jar_path:
            self._scan_jar(self.jar_path)
        for res_path in self.res_paths:
            self._scan_resources(res_path)
        for src_path in self.src_paths:
            self._scan_sources(src_path)
        self._infer_relationships()

    def _scan_resources(self, res_root: Path) -> None:
        for path in res_root.rglob("mods.toml"):
            text = read_text(path)
            modid_match = re.search(r"modId\s*=\s*\"([^\"]+)\"", text)
            if modid_match:
                self.modid = modid_match.group(1)
            version_match = re.search(r"version\s*=\s*\"([^\"]+)\"", text)
            if version_match:
                self.mod_version = version_match.group(1)
        if self.modid:
            data_root = res_root / "data" / self.modid
            if data_root.exists():
                tag_root = data_root / "tags"
                for tag_file in tag_root.rglob("*.json"):
                    rel = tag_file.relative_to(tag_root)
                    parts = rel.parts
                    if len(parts) >= 2:
                        kind = parts[0]
                        tag_path = "/".join(parts[1:]).replace(".json", "")
                        self.tags.add((kind, tag_path))

    def _scan_sources(self, src_root: Path) -> None:
        for java_file in src_root.rglob("*.java"):
            rel_path = java_file.relative_to(src_root)
            text = read_text(java_file)
            package_match = PACKAGE_RE.search(text)
            if package_match:
                self.packages.add(package_match.group(1))
            self._scan_java_file(java_file, rel_path, text)

    def _scan_jar(self, jar_path: Path) -> None:
        with zipfile.ZipFile(jar_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("mods.toml"):
                    text = zf.read(name).decode("utf-8", errors="ignore")
                    modid_match = re.search(r"modId\s*=\s*\"([^\"]+)\"", text)
                    if modid_match:
                        self.modid = self.modid or modid_match.group(1)
                    version_match = re.search(r"version\s*=\s*\"([^\"]+)\"", text)
                    if version_match:
                        self.mod_version = self.mod_version or version_match.group(1)
                if name.endswith(".class"):
                    lowered = name.lower()
                    if any(keyword in lowered for keyword in MULTIBLOCK_KEYWORDS):
                        base = Path(name).stem
                        self.multiblocks.setdefault(base, {"classes": set(), "assets": set(), "notes": set()})
                        self.multiblocks[base]["classes"].add(name.replace("/", ".").rstrip(".class"))
        # Tags from jar assets
            for name in zf.namelist():
                if name.startswith("data/") and name.endswith(".json") and "/tags/" in name and self.modid:
                    tag_path = name.split("/tags/")[1].rsplit(".json", 1)[0]
                    kind = name.split("/tags/")[0].split("/")[-1]
                    self.tags.add((kind, tag_path))

    def _scan_java_file(self, path: Path, rel_path: Path, text: str) -> None:
        full_rel = rel_path.as_posix()
        deferred_matches = {m.group(2): m.group(1) for m in DEFERRED_RE.finditer(text)}
        for match in CAPABILITY_RE.finditer(text):
            key = f"ForgeCapabilities.{match.group(1)}"
            entry = self.capabilities.setdefault(key, CapabilityEntry(key=key))
            entry.providers.add(full_rel)
            self.file_capabilities[path].add(key)
        for match in ATTACH_EVENT_RE.finditer(text):
            key = match.group(1)
            entry = self.capabilities.setdefault(key, CapabilityEntry(key=key))
            entry.attach_points.add(f"{full_rel}")
            entry.notes.add("INFERRED: attaches capability")
        if MENU_HINTS.search(text):
            self.file_menu_hints[path] = True
        if ENERGY_HINTS.search(text):
            self.file_energy_hints[path] = True
        lowered = text.lower()
        for keyword in MULTIBLOCK_KEYWORDS:
            if self._keyword_present(lowered, keyword):
                self.file_multiblock_hint[path].add(keyword)
        for var, reg_type in deferred_matches.items():
            category = self._categorize_registry_type(reg_type)
            if not category:
                continue
            for match in REGISTER_CALL_RE.finditer(text):
                if match.group(1) != var:
                    continue
                identifier = match.group(2)
                key = (category, identifier)
                entry = self.registry_entries.setdefault(key, RegistryEntry(category=category, identifier=identifier))
                entry.source = entry.source or full_rel
                supplier_new = SUPPLIER_NEW_RE.search(text, match.end())
                if supplier_new and supplier_new.group(1) == identifier:
                    entry.class_name = entry.class_name or supplier_new.group(2)
                supplier_ref = SUPPLIER_REF_RE.search(text, match.end())
                if supplier_ref and supplier_ref.group(1) == identifier:
                    entry.class_name = entry.class_name or supplier_ref.group(2)
                entry.notes.append("DECLARED via DeferredRegister")
        for match in SIMPLE_CHANNEL_RE.finditer(text):
            args = match.group(1)
            resloc = re.search(r"ResourceLocation\(([^\)]+)\)", args)
            if resloc:
                self.network_channel = resloc.group(1).replace(" ", "")
        proto_match = PROTOCOL_VERSION_RE.search(text)
        if proto_match:
            self.network_protocol = proto_match.group(1)
        for match in REGISTER_MESSAGE_RE.finditer(text):
            args = match.group(1)
            parts = [p.strip() for p in args.split(",") if p.strip()]
            if parts:
                cls_part = parts[1] if len(parts) > 1 else parts[0]
                cls_part = cls_part.replace(".class", "")
                packet = self.packet_entries.setdefault(cls_part, PacketEntry(class_name=cls_part))
                if len(parts) >= 4:
                    handler = parts[3]
                    if "Server" in handler or "server" in handler:
                        packet.direction = "C2S"
                    elif "Client" in handler or "client" in handler:
                        packet.direction = "S2C"
                    else:
                        packet.direction = "both"
                packet.notes.append(f"DECLARED in {full_rel}")
        if EVENTBUS_RE.search(text):
            self.events.add((full_rel, "Mod.EventBusSubscriber", "both"))
        if SUBSCRIBE_EVENT_RE.search(text):
            self.events.add((full_rel, "@SubscribeEvent", "both"))
        for config_match in CONFIG_DEFINE_RE.finditer(text):
            key = config_match.group(1)
            default = config_match.group(2).strip()
            range_val = config_match.group(3).strip() if config_match.group(3) else None
            scope = "UNKNOWN"
            if "COMMON" in text:
                scope = "COMMON"
            elif "CLIENT" in text:
                scope = "CLIENT"
            elif "SERVER" in text:
                scope = "SERVER"
            cfg_key = (scope, key)
            entry = self.config_entries.setdefault(cfg_key, ConfigEntry(scope=scope, key=key, default=default, value_range=range_val))
            entry.notes.append(f"DECLARED in {full_rel}")

        # Multiblock/Reactor hints
        qualified_name = self._qualified_class_name(text)
        qualified_lower = qualified_name.lower()
        path_lower = full_rel.lower()
        for keyword in MULTIBLOCK_KEYWORDS:
            if self._keyword_present(lowered, keyword):
                name = self._extract_class_name(text) or full_rel
                mult = self.multiblocks.setdefault(name, {"classes": set(), "assets": set(), "notes": set()})
                mult["classes"].add(qualified_name)
                mult["notes"].add(f"INFERRED keyword '{keyword}' in {full_rel}")
        if any(self._keyword_present(lowered, k) for k in REACTOR_KEYWORDS):
            name = self._extract_class_name(text) or full_rel
            reactor = self.reactors.setdefault(name, {"classes": set(), "blueprints": set(), "io": {"energy": "", "fluids": [], "items": []}, "notes": set()})
            reactor["classes"].add(qualified_name)
            if self.file_energy_hints.get(path):
                reactor["io"]["energy"] = reactor["io"].get("energy") or "INFERRED: uses Forge energy"
            reactor["notes"].add(f"INFERRED from keywords in {full_rel}")
        if any(k in qualified_lower or k in path_lower for k in CABLE_KEYWORDS) or any(self._keyword_present(lowered, k) for k in CABLE_KEYWORDS):
            name = self._extract_class_name(text) or full_rel
            cable = self.cables.setdefault(name, {"class": qualified_name, "capacity": "?", "tier": "?", "loss": "?", "notes": set()})
            if self.file_energy_hints.get(path):
                cable["notes"].add("INFERRED: interacts with energy capability")

    def _extract_class_name(self, text: str) -> Optional[str]:
        match = CLASS_RE.search(text)
        if match:
            return match.group(1)
        return None

    def _qualified_class_name(self, text: str) -> str:
        pkg_match = PACKAGE_RE.search(text)
        class_match = CLASS_RE.search(text)
        if pkg_match and class_match:
            return f"{pkg_match.group(1)}.{class_match.group(1)}"
        if class_match:
            return class_match.group(1)
        return ""

    def _keyword_present(self, lowered: str, keyword: str) -> bool:
        if not keyword:
            return False
        if keyword.isalpha():
            pattern = rf"\b{re.escape(keyword)}\b"
            return re.search(pattern, lowered) is not None
        return keyword in lowered

    def _categorize_registry_type(self, reg_type: str) -> Optional[str]:
        for hint, category in REGISTRY_CATEGORY_HINTS.items():
            if hint in reg_type:
                return category
        return None

    def _infer_relationships(self) -> None:
        # Add capability notes to registry entries based on file hints
        for (category, identifier), entry in self.registry_entries.items():
            source_path = entry.source
            if not source_path:
                continue
            src_path = None
            for root in self.src_paths:
                candidate = root / source_path
                if candidate.exists():
                    src_path = candidate
                    break
            if not src_path:
                continue
            caps = self.file_capabilities.get(src_path, set())
            if caps:
                entry.notes.append("INFERRED: references " + ", ".join(sorted(caps)))
            if self.file_menu_hints.get(src_path):
                entry.notes.append("INFERRED: menu interactions")
            if self.file_energy_hints.get(src_path):
                entry.notes.append("INFERRED: energy-related logic")

    # endregion

    def summarize(self) -> Dict[str, int]:
        summary = defaultdict(int)
        for (_, _), entry in self.registry_entries.items():
            summary[entry.category] += 1
        summary["capabilities"] = len(self.capabilities)
        summary["multiblocks"] = len(self.multiblocks)
        summary["reactors"] = len(self.reactors)
        summary["cables"] = len(self.cables)
        summary["packets"] = len(self.packet_entries)
        summary["configs"] = len(self.config_entries)
        summary["tags"] = len(self.tags)
        return summary

    # region: output helpers
    def write_outputs(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._write_api_overview()
        self._write_api_index_json()
        self._write_api_index_csv()
        self._write_mermaid()
        self._write_scan_report()

    def _write_api_overview(self) -> None:
        path = self.out_dir / "API_OVERVIEW.md"
        sections: List[str] = []
        sections.append("# API Overview\n")
        sections.append("## Identity\n")
        sections.append(f"- **Mod ID:** `{self.modid or 'unknown'}`\n")
        if self.mod_version:
            sections.append(f"- **Version:** `{self.mod_version}`\n")
        if self.packages:
            sections.append(f"- **Packages:** {', '.join(sorted(self.packages))}\n")
        sections.append("\n")

        def build_registry_section(title: str, category: str) -> None:
            sections.append(f"## {title}\n")
            entries = [e for e in self.registry_entries.values() if e.category == category]
            if not entries:
                sections.append("*No references discovered.*\n")
            else:
                for entry in sorted(entries, key=lambda e: e.identifier):
                    id_value = entry.identifier
                    if self.modid and ":" not in id_value:
                        id_value = f"{self.modid}:{id_value}"
                    sections.append(f"- `{id_value}` → `{entry.class_name or 'unknown class'}` ({entry.source or 'unknown source'})\n")
                    if entry.notes:
                        sections.append(f"  - Notes: {', '.join(sorted(set(entry.notes)))}\n")
            sections.append("**What to look for in an implementation**\n")
            sections.append("- Ensure registration with DeferredRegister or equivalent.\n")
            sections.append("- Provide matching JSON assets (`models`, `blockstates`, `lang`).\n")
            sections.append("- Verify capability and menu expectations from notes.\n\n")

        build_registry_section("Blocks", "blocks")
        build_registry_section("Items", "items")
        build_registry_section("Block Entities", "block_entities")
        build_registry_section("Menus", "menus")
        build_registry_section("Entities", "entities")
        build_registry_section("Fluids", "fluids")
        build_registry_section("Recipe Serializers", "recipes")
        build_registry_section("Sounds", "sounds")

        sections.append("## Multiblock / Structure Concepts\n")
        if not self.multiblocks:
            sections.append("*No multiblock hints discovered.*\n")
        else:
            for name, data in sorted(self.multiblocks.items()):
                classes = ", ".join(sorted(filter(None, data.get("classes", []))))
                notes = ", ".join(sorted(data.get("notes", [])))
                sections.append(f"- **{name}**: {classes or 'unknown classes'}\n")
                if notes:
                    sections.append(f"  - Notes: {notes}\n")
        sections.append("**What to look for in an implementation**\n")
        sections.append("- Validate structure dimensions & casing blocks.\n")
        sections.append("- Provide blueprint or pattern assets if required.\n")
        sections.append("- Coordinate block entities for controllers/hatches.\n\n")

        sections.append("## Energy / Cables / Networks\n")
        if not self.cables and not self.capabilities:
            sections.append("*No energy constructs discovered.*\n")
        else:
            for name, data in sorted(self.cables.items()):
                sections.append(f"- **{name}** (`{data.get('class', '')}`) capacity `{data.get('capacity')}` tier `{data.get('tier')}` loss `{data.get('loss')}`\n")
                notes = data.get("notes")
                if notes:
                    sections.append(f"  - Notes: {', '.join(sorted(notes))}\n")
            for cap in sorted(self.capabilities.values(), key=lambda c: c.key):
                sections.append(f"- Capability `{cap.key}` from {', '.join(sorted(cap.providers)) or 'unknown'}\n")
                if cap.notes:
                    sections.append(f"  - Notes: {', '.join(sorted(cap.notes))}\n")
        sections.append("**What to look for in an implementation**\n")
        sections.append("- Expose/consume `ForgeCapabilities.ENERGY` where noted.\n")
        sections.append("- Respect IO direction and tier hints in API docs.\n")
        sections.append("- Ensure cables synchronize with network packets if present.\n\n")

        sections.append("## Networking\n")
        sections.append(f"- Channel: `{self.network_channel or 'unknown'}`\n")
        sections.append(f"- Protocol: `{self.network_protocol or 'unspecified'}`\n")
        if not self.packet_entries:
            sections.append("*No packets discovered.*\n")
        else:
            for packet in sorted(self.packet_entries.values(), key=lambda p: p.class_name):
                sections.append(f"- `{packet.class_name}` direction `{packet.direction}`\n")
                if packet.notes:
                    sections.append(f"  - Notes: {', '.join(sorted(set(packet.notes)))}\n")
        sections.append("**What to look for in an implementation**\n")
        sections.append("- Register packets on both client & server with matching protocol.\n")
        sections.append("- Handle thread safety in packet handlers.\n")
        sections.append("- Keep protocol version synchronized with PROTOCOL_VERSION constant.\n\n")

        sections.append("## Events & Hooks\n")
        if not self.events:
            sections.append("*No event subscribers detected.*\n")
        else:
            for clazz, event, side in sorted(self.events):
                sections.append(f"- `{clazz}` listens for `{event}` on `{side}`\n")
        sections.append("**What to look for in an implementation**\n")
        sections.append("- Annotate subscriber classes with the proper mod id.\n")
        sections.append("- Guard client-only listeners with `Dist.CLIENT`.\n")
        sections.append("- Avoid heavy logic on global event bus handlers.\n\n")

        sections.append("## Configs\n")
        if not self.config_entries:
            sections.append("*No ForgeConfigSpec usage detected.*\n")
        else:
            for config in sorted(self.config_entries.values(), key=lambda c: (c.scope, c.key)):
                sections.append(f"- `{config.scope}` → `{config.key}` default `{config.default}` range `{config.value_range or 'n/a'}`\n")
                if config.notes:
                    sections.append(f"  - Notes: {', '.join(sorted(set(config.notes)))}\n")
        sections.append("**What to look for in an implementation**\n")
        sections.append("- Sync config defaults with gameplay balance.\n")
        sections.append("- Document valid ranges for pack makers.\n")
        sections.append("- Hook config reload events if runtime adjustments are required.\n\n")

        sections.append("## Datagen & Assets\n")
        if not self.tags:
            sections.append("*No explicit asset hints beyond default registries.*\n")
        else:
            for kind, tag in sorted(self.tags):
                sections.append(f"- Tag `{kind}:{tag}` referenced in resources\n")
        sections.append("**What to look for in an implementation**\n")
        sections.append("- Provide tag JSON files for API contracts.\n")
        sections.append("- Ensure loot tables and recipes align with registry ids.\n")
        sections.append("- Include localization entries for API-facing names.\n")

        path.write_text("".join(sections), encoding="utf-8")

    def _write_api_index_json(self) -> None:
        data = {
            "modid": self.modid,
            "packages": sorted(self.packages),
            "registries": {
                key: [entry.to_json(self.modid) for entry in sorted(self.registry_entries.values(), key=lambda e: e.identifier) if entry.category == key]
                for key in ["blocks", "items", "block_entities", "entities", "menus", "fluids", "recipes", "sounds"]
            },
            "capabilities": [cap.to_json() for cap in sorted(self.capabilities.values(), key=lambda c: c.key)],
            "multiblocks": [
                {
                    "name": name,
                    "classes": sorted(filter(None, data.get("classes", []))),
                    "assets": sorted(filter(None, data.get("assets", []))),
                    "notes": "; ".join(sorted(data.get("notes", []))) if data.get("notes") else "",
                }
                for name, data in sorted(self.multiblocks.items())
            ],
            "reactors": [
                {
                    "name": name,
                    "classes": sorted(filter(None, data.get("classes", []))),
                    "blueprints": sorted(filter(None, data.get("blueprints", []))),
                    "io": data.get("io", {}),
                    "notes": "; ".join(sorted(data.get("notes", []))) if data.get("notes") else "",
                }
                for name, data in sorted(self.reactors.items())
            ],
            "cables": [
                {
                    "name": name,
                    "class": data.get("class", ""),
                    "capacity": data.get("capacity", ""),
                    "tier": data.get("tier", ""),
                    "loss": data.get("loss", ""),
                    "notes": "; ".join(sorted(data.get("notes", []))) if data.get("notes") else "",
                }
                for name, data in sorted(self.cables.items())
            ],
            "network": {
                "channel": self.network_channel or "",
                "protocol": self.network_protocol or "",
                "packets": [packet.to_json() for packet in sorted(self.packet_entries.values(), key=lambda p: p.class_name)],
            },
            "configs": [cfg.to_json() for cfg in sorted(self.config_entries.values(), key=lambda c: (c.scope, c.key))],
            "events": [
                {
                    "class": clazz,
                    "event": event,
                    "side": side,
                    "notes": "",
                }
                for clazz, event, side in sorted(self.events)
            ],
            "tags": [
                {
                    "kind": kind,
                    "path": tag,
                }
                for kind, tag in sorted(self.tags)
            ],
        }
        (self.out_dir / "api_index.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _write_api_index_csv(self) -> None:
        rows: List[List[str]] = []
        for entry in sorted(self.registry_entries.values(), key=lambda e: (e.category, e.identifier)):
            rows.append(entry.to_csv_row(self.modid))
        for cap in sorted(self.capabilities.values(), key=lambda c: c.key):
            rows.extend(cap.to_csv_rows())
        for cfg in sorted(self.config_entries.values(), key=lambda c: (c.scope, c.key)):
            rows.append(cfg.to_csv_row())
        path = self.out_dir / "api_index.csv"
        with path.open("w", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["kind", "id_or_key", "class", "source", "notes"])
            writer.writerows(rows)

    def _write_mermaid(self) -> None:
        lines = ["graph TD"]
        for (category, identifier), entry in sorted(self.registry_entries.items()):
            node_name = f"{category}_{identifier}".replace(":", "_").replace("-", "_")
            lines.append(f"  {node_name}[{category}: {identifier}]")
            caps = []
            if entry.notes:
                for note in entry.notes:
                    for cap in self.capabilities:
                        if cap in note:
                            caps.append(cap)
            for cap in set(caps):
                cap_node = cap.replace('.', '_')
                lines.append(f"  {node_name} -->|capability| {cap_node}[{cap}]")
        for packet in self.packet_entries.values():
            node_name = packet.class_name.replace('.', '_')
            lines.append(f"  NetworkChannel --> {node_name}[Packet: {packet.class_name}]")
        if self.network_channel:
            lines.append(f"  Root[Mod API] -->|network| NetworkChannel[{self.network_channel}]")
        for name in self.multiblocks:
            lines.append(f"  Root --> {name}_Multiblock[Multiblock: {name}]")
        for name in self.reactors:
            lines.append(f"  Root --> {name}_Reactor[Reactor: {name}]")
        for name in self.cables:
            lines.append(f"  Root --> {name}_Cable[Cable: {name}]")
        (self.out_dir / "relationships.mmd").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_scan_report(self) -> None:
        summary = self.summarize()
        lines = ["API Inventory Scan Report", "============================", ""]
        for key in ["blocks", "items", "block_entities", "menus", "entities", "fluids", "recipes", "sounds", "capabilities", "multiblocks", "reactors", "cables", "packets", "configs", "tags"]:
            lines.append(f"{key}: {summary.get(key, 0)}")
        lines.append("")
        lines.append("Heuristics:")
        lines.append("- Entries marked as INFERRED originate from keyword or pattern matches; validate manually.\n")
        (self.out_dir / "scan_report.txt").write_text("\n".join(lines), encoding="utf-8")


# endregion

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate API inventory artifacts.")
    parser.add_argument("--src", action="append", type=Path, default=[], help="Source directories to scan")
    parser.add_argument("--res", action="append", type=Path, default=[], help="Resource directories to scan")
    parser.add_argument("--jar", type=Path, default=None, help="Optional API jar to scan")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    indexer = APIIndexer(args.src, args.res, args.jar, args.out)
    indexer.scan()
    indexer.write_outputs()
    summary = indexer.summarize()
    print("API inventory generated:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"Artifacts written to {indexer.out_dir / 'API_OVERVIEW.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
