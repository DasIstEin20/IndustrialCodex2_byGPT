# Forge 1.20.1 Migration Audit

This document captures the current 1.19.2 codebase state before starting the multi-PR migration plan. It highlights where modernization work is required to reach Forge 47.x / Minecraft 1.20.1 parity.

| Subsystem | Current State | 1.20.1 Target | Blockers / Notes |
| --- | --- | --- | --- |
| Build / Gradle | ForgeGradle 5.1 with Forge 1.19.2-43.1.47 and official Mojang mappings; uses legacy `archivesBaseName`/`examplemod` scaffolding in run configs. | Move to ForgeGradle 6+, Forge 47.x for 1.20.1, Mojang + latest Parchment mappings, and modern Gradle 8 idioms with `mods.toml` alignment. | Requires reworking dependency versions, removing example scaffolding, and validating new plugin DSL. 【F:build.gradle†L1-L145】 |
| Java Toolchain | Toolchain already set to Java 17. | Keep Java 17 but enforce via Gradle toolchain / CI. | Verify compatibility with newer Gradle wrapper and IDE import. 【F:build.gradle†L11-L13】 |
| Run Configurations | Client/server/data runs still reference the placeholder `examplemod` namespace. | Replace with real mod id, ensure datagen args and gametest namespaces match final IDs. | Determine canonical mod id before updating configs. 【F:build.gradle†L35-L111】 |
| Source Layout & Mod Entry | `src/main/java` only exposes API-facing packages (e.g., addon hooks), no `@Mod` entrypoint or DeferredRegister usage is present. | Introduce `@Mod` bootstrap class that wires registries/events via `IEventBus`. | Need to import or recreate the gameplay module alongside the API. 【F:src/main/java/ic2/api/addons/IModule.java†L1-L35】 |
| Registries | No centralized registry helpers; gameplay content is absent from this repository build. | Recreate block/item/BE/menus/etc. registries using DeferredRegister. | Source for actual content must be ported from original mod or reimplemented. 【F:src/main/java/ic2/api/addons/IModule.java†L14-L35】 |
| Events & Lifecycle | Plugin API references legacy `preInit`/`postInit` concepts, implying old lifecycle handling. | Adopt 1.20.1 lifecycle (`FMLCommonSetupEvent`, `RegisterEvent`, `ClientSetupEvent`, etc.) with `@Mod.EventBusSubscriber`. | Need to map historic phases onto current events without breaking addon API. 【F:src/main/java/ic2/api/addons/IModule.java†L18-L35】 |
| Networking | Custom `INetworkManager` API expects bespoke buffers and GUI sync routines. | Replace with Forge `SimpleChannel` packets with explicit protocol version, codecs, and side-safe handlers. | Must bridge existing API expectations for addons while migrating implementation. 【F:src/main/java/ic2/api/network/INetworkManager.java†L1-L59】 |
| Capabilities & Storage | No capability registration/attach code in repo; API references assume classic capability hooks. | Rebuild capabilities on top of `ForgeCapabilities` with `AttachCapabilitiesEvent`. | Requires recovering concrete capability classes from original mod. 【F:src/main/java/ic2/api/network/INetworkManager.java†L41-L57】 |
| Config System | API comments mention an internal config loader incompatible with Forge configs, but no actual `ForgeConfigSpec` usage. | Implement COMMON/CLIENT/SERVER configs via `ForgeConfigSpec` with hot-load safety and map addon hooks onto it. | Need design to preserve addon access to configs without legacy static singletons. 【F:src/main/java/ic2/api/addons/IModule.java†L18-L25】 |
| Data Generation | Gradle run config points to `examplemod` datagen; there are no datagen provider classes. | Add datagen entrypoint covering blockstates, models, loot tables, tags, recipes, advancements, and lang. | Requires reconstructing content definitions first. 【F:build.gradle†L96-L111】 |
| Assets / Localization | Resource tree currently contains only localization JSONs for many languages; no blockstate/models/loot definitions are present. | Regenerate assets from datagen and prune unused legacy translations. | Need to audit translation keys against restored content. 【F:src/main/resources/assets/ic2/lang/blocks_en_us.json†L1-L32】 |
| Documentation | README still describes a "1.19.2 IC2Classic API" and lacks migration guidance. | Update README/BUILDING/CONTRIBUTING/CHANGELOG plus dedicated 1.20.1 migration notes. | Documentation should reflect new build steps and multi-PR approach. 【F:README.md†L1-L7】 |

## Immediate Follow-ups

1. Prepare build-system upgrade PR targeting Forge 1.20.1 / Gradle 8 and set baseline mappings.
2. Reintroduce the gameplay module (or vendor upstream source) so registries, events, networking, and assets can be migrated in subsequent PRs.
3. Define the canonical mod id and artifact coordinates before rewriting run configs and data generation outputs.
