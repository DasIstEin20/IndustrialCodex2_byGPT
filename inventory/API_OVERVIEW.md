# API Overview
## Identity
- **Mod ID:** `unknown`
- **Packages:** ic2.api.addons, ic2.api.blocks, ic2.api.blocks.wrench, ic2.api.core, ic2.api.crops, ic2.api.energy, ic2.api.energy.impl, ic2.api.energy.tile, ic2.api.events, ic2.api.items, ic2.api.items.armor, ic2.api.items.electric, ic2.api.items.readers, ic2.api.network, ic2.api.network.buffer, ic2.api.network.container, ic2.api.network.item, ic2.api.network.tile, ic2.api.reactor, ic2.api.reactor.planner, ic2.api.recipes, ic2.api.recipes.ingridients.generators, ic2.api.recipes.ingridients.inputs, ic2.api.recipes.ingridients.queue, ic2.api.recipes.ingridients.recipes, ic2.api.recipes.misc, ic2.api.recipes.registries, ic2.api.ticks, ic2.api.tiles, ic2.api.tiles.display, ic2.api.tiles.display.impl, ic2.api.tiles.readers, ic2.api.tiles.teleporter, ic2.api.tiles.tubes, ic2.api.util

## Blocks
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Items
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Block Entities
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Menus
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Entities
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Fluids
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Recipe Serializers
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Sounds
*No references discovered.*
**What to look for in an implementation**
- Ensure registration with DeferredRegister or equivalent.
- Provide matching JSON assets (`models`, `blockstates`, `lang`).
- Verify capability and menu expectations from notes.

## Multiblock / Structure Concepts
- **BaseDurabilitySimulatedStack**: ic2.api.reactor.planner.BaseDurabilitySimulatedStack
  - Notes: INFERRED keyword 'planner' in ic2/api/reactor/planner/BaseDurabilitySimulatedStack.java, INFERRED keyword 'reactor' in ic2/api/reactor/planner/BaseDurabilitySimulatedStack.java
- **BaseHeatSimulatedStack**: ic2.api.reactor.planner.BaseHeatSimulatedStack
  - Notes: INFERRED keyword 'planner' in ic2/api/reactor/planner/BaseHeatSimulatedStack.java, INFERRED keyword 'reactor' in ic2/api/reactor/planner/BaseHeatSimulatedStack.java
- **FloatTracker**: ic2.api.reactor.planner.FloatTracker
  - Notes: INFERRED keyword 'planner' in ic2/api/reactor/planner/FloatTracker.java, INFERRED keyword 'reactor' in ic2/api/reactor/planner/FloatTracker.java
- **IChamberReactor**: ic2.api.reactor.IChamberReactor
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/IChamberReactor.java
- **IReactor**: ic2.api.reactor.IReactor
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/IReactor.java
- **IReactorChamber**: ic2.api.reactor.IReactorChamber
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/IReactorChamber.java
- **IReactorComponent**: ic2.api.reactor.IReactorComponent
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/IReactorComponent.java
- **IReactorPlannerComponent**: ic2.api.reactor.IReactorPlannerComponent
  - Notes: INFERRED keyword 'planner' in ic2/api/reactor/IReactorPlannerComponent.java, INFERRED keyword 'reactor' in ic2/api/reactor/IReactorPlannerComponent.java
- **IReactorProduct**: ic2.api.reactor.IReactorProduct
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/IReactorProduct.java
- **ISimulatedReactor**: ic2.api.reactor.planner.ISimulatedReactor
  - Notes: INFERRED keyword 'planner' in ic2/api/reactor/planner/ISimulatedReactor.java, INFERRED keyword 'reactor' in ic2/api/reactor/planner/ISimulatedReactor.java
- **ISteamReactor**: ic2.api.reactor.ISteamReactor
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/ISteamReactor.java
- **ISteamReactorChamber**: ic2.api.reactor.ISteamReactorChamber
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/ISteamReactorChamber.java
- **IUsableUranium**: ic2.api.reactor.IUsableUranium
  - Notes: INFERRED keyword 'reactor' in ic2/api/reactor/IUsableUranium.java
- **SimulatedStack**: ic2.api.reactor.planner.SimulatedStack
  - Notes: INFERRED keyword 'planner' in ic2/api/reactor/planner/SimulatedStack.java, INFERRED keyword 'reactor' in ic2/api/reactor/planner/SimulatedStack.java
- **Tracker**: ic2.api.reactor.planner.Tracker
  - Notes: INFERRED keyword 'planner' in ic2/api/reactor/planner/Tracker.java, INFERRED keyword 'reactor' in ic2/api/reactor/planner/Tracker.java
**What to look for in an implementation**
- Validate structure dimensions & casing blocks.
- Provide blueprint or pattern assets if required.
- Coordinate block entities for controllers/hatches.

## Energy / Cables / Networks
- **FoamEvent** (`ic2.api.events.FoamEvent`) capacity `?` tier `?` loss `?`
- **IWrenchable** (`ic2.api.blocks.IWrenchable`) capacity `?` tier `?` loss `?`
**What to look for in an implementation**
- Expose/consume `ForgeCapabilities.ENERGY` where noted.
- Respect IO direction and tier hints in API docs.
- Ensure cables synchronize with network packets if present.

## Networking
- Channel: `unknown`
- Protocol: `unspecified`
*No packets discovered.*
**What to look for in an implementation**
- Register packets on both client & server with matching protocol.
- Handle thread safety in packet handlers.
- Keep protocol version synchronized with PROTOCOL_VERSION constant.

## Events & Hooks
*No event subscribers detected.*
**What to look for in an implementation**
- Annotate subscriber classes with the proper mod id.
- Guard client-only listeners with `Dist.CLIENT`.
- Avoid heavy logic on global event bus handlers.

## Configs
*No ForgeConfigSpec usage detected.*
**What to look for in an implementation**
- Sync config defaults with gameplay balance.
- Document valid ranges for pack makers.
- Hook config reload events if runtime adjustments are required.

## Datagen & Assets
*No explicit asset hints beyond default registries.*
**What to look for in an implementation**
- Provide tag JSON files for API contracts.
- Ensure loot tables and recipes align with registry ids.
- Include localization entries for API-facing names.
