# IndustrialCodex2 API Behavior Map

## Energy / Cables
### Network management
- [DECLARED] **EnergyNet.INSTANCE** exposes a mutable singleton hook; implementations must inject an `IEnergyNet` before any tiles register.
- [DECLARED] **IEnergyNet** supplies grid lookup (`getTile`, `getSubTile`, `getTiles`) and lifecycle callbacks (`addTile`, `removeTile`, `updateTile`). Implementations must translate world/position pairs to the matching `IEnergyTile`. 【F:src/main/java/ic2/api/energy/IEnergyNet.java†L1-L42】
- [DECLARED] `IEnergyNet.getPowerFromTier(int)` and `getTierFromPower(int)` form the canonical tier↔packet size mapping in EU units. `getDisplayTier(int)` exposes localization-friendly tier names. 【F:src/main/java/ic2/api/energy/IEnergyNet.java†L18-L24】
- [DECLARED] `IEnergyNet.getStats` and `getPacketStats` return aggregated `TransferStats` and per-packet `PacketStats` snapshots, indicating how much EU flowed in/out and whether a sink accepted packets. 【F:src/main/java/ic2/api/energy/IEnergyNet.java†L24-L40】【F:src/main/java/ic2/api/energy/TransferStats.java†L1-L35】【F:src/main/java/ic2/api/energy/PacketStats.java†L1-L35】

### Tiles & conductors
- [DECLARED] **IEnergyTile** inherits `ILocation`, so every tile must supply world/position context either via `BlockEntity` or explicit overrides. 【F:src/main/java/ic2/api/energy/tile/IEnergyTile.java†L1-L6】【F:src/main/java/ic2/api/util/ILocation.java†L1-L29】
- [DECLARED] **IEnergyAcceptor** and **IEnergyEmitter** define directional gating via `canAcceptEnergy` / `canEmitEnergy`, called per-side before any transfer. 【F:src/main/java/ic2/api/energy/tile/IEnergyAcceptor.java†L1-L8】【F:src/main/java/ic2/api/energy/tile/IEnergyEmitter.java†L1-L8】
- [DECLARED] **IEnergySink** sets per-sink behavior: `getSinkTier`, `getRequestedEnergy`, and `acceptEnergy(Direction side, int amount, int voltage)` to consume EU and report leftovers. 【F:src/main/java/ic2/api/energy/tile/IEnergySink.java†L1-L12】
- [DECLARED] **IEnergySource** reports available EU (`getProvidedEnergy`, `getMaxEnergyOutput`), consumes the transferred amount via `consumeEnergy`, and may receive `onPacketFailed` callbacks when the net cannot route energy. Optional `SourceType` metadata distinguishes active/passive producers. 【F:src/main/java/ic2/api/energy/tile/IEnergySource.java†L1-L28】
- [DECLARED] **IMultiEnergyTile/Source** bundle logical tiles or packet emitters; `IMultiEnergySource` exposes packet count info for multi-emission designs. 【F:src/main/java/ic2/api/energy/tile/IMultiEnergyTile.java†L1-L7】【F:src/main/java/ic2/api/energy/tile/IMultiEnergySource.java†L1-L7】
- [DECLARED] **IEnergyConductor** bridges acceptor/emitter roles and reports physical properties: conduction loss (EU/tick), insulation absorption/breakdown thresholds, conductor breakdown, and removal hooks when overloaded or stripped. The default `isWaterlogged` helper inspects the hosting block state. 【F:src/main/java/ic2/api/energy/tile/IEnergyConductor.java†L1-L24】
- [DECLARED] **IEnergyConductorModifiable** exposes runtime insulation toggles, while **IEnergyConductorColored** reports dye channels for routing overlays. Anchored conductors implement **IAnchorTile** to manage mechanical anchors per side. 【F:src/main/java/ic2/api/energy/tile/IEnergyConductorModifiable.java†L1-L8】【F:src/main/java/ic2/api/energy/tile/IEnergyConductorColored.java†L1-L8】【F:src/main/java/ic2/api/energy/tile/IEnergyConductorAnchored.java†L1-L6】【F:src/main/java/ic2/api/tiles/IAnchorTile.java†L1-L10】

### Convenience wrappers
- [DECLARED] **LinkedSink** / **LinkedSource** wrap bare block positions into temporary `IEnergyAcceptor`/`IEnergyEmitter` views, gating transfers by bitmask of allowed directions. Intended for multipart or multi-block controllers bridging into the net. 【F:src/main/java/ic2/api/energy/impl/LinkedSink.java†L1-L64】【F:src/main/java/ic2/api/energy/impl/LinkedSource.java†L1-L64】

#### Implementation checklist
- Ensure every energy tile returns stable world/position info via `ILocation`. [DECLARED]
- Validate side-based access in `canAcceptEnergy` / `canEmitEnergy` before exposing neighbors. [DECLARED]
- Clamp sink tiers/voltages to supported packet sizes using `IEnergyNet.getPowerFromTier`. [DECLARED]
- Update energy requests before each tick so the net can plan packet routing. [INFERRED]
- Surface insulation and breakdown values that match in-game cable specs to avoid desync. [INFERRED]
- Call `consumeEnergy` only after the net confirms delivery to avoid duplicating EU. [DECLARED]
- Invoke `updateTile` on state changes (tier, demand) so the grid recalculates flows. [INFERRED]
- Provide SourceType metadata for proper transformer/producer heuristics. [INFERRED]

## Reactor / Planner
### Core reactor contracts
- [DECLARED] **IReactor** exposes core heat bookkeeping (`getHeat`/`setHeat`/`addHeat`), capacity (`getMaxHeat`), heat effect modifier, per-tick energy accumulation, slot inventory (`getStackInReactor`/`setStackInReactor`), explosion trigger, tick interval, and production flag. EU output is modeled as double precision per tick. 【F:src/main/java/ic2/api/reactor/IReactor.java†L1-L32】
- [DECLARED] **IChamberReactor** extends `IReactor` for expandable chambers, reporting grid dimensions and allowing `refreshChambers()` after structure changes. 【F:src/main/java/ic2/api/reactor/IChamberReactor.java†L1-L9】
- [DECLARED] **IReactorChamber** surfaces a link back to the master reactor tile, while **ISteamReactorChamber** marks steam-specific chambers. 【F:src/main/java/ic2/api/reactor/IReactorChamber.java†L1-L6】【F:src/main/java/ic2/api/reactor/ISteamReactorChamber.java†L1-L5】
- [DECLARED] **ISteamReactor** augments the core contract with `FluidTank` accessors for water/steam buffers, ensuring steam builds can pipe fluids. 【F:src/main/java/ic2/api/reactor/ISteamReactor.java†L1-L9】

### Components & products
- [DECLARED] **IReactorProduct** validates whether an `ItemStack` can occupy a reactor slot (`isValidForReactor`). Components default to `true`. 【F:src/main/java/ic2/api/reactor/IReactorProduct.java†L1-L7】【F:src/main/java/ic2/api/reactor/IReactorComponent.java†L1-L17】
- [DECLARED] **IReactorComponent** drives per-slot simulation: `processChamber` (heat vs. damage phases), `acceptUraniumPulse` (cross-slot neutron interactions), heat storage queries (`canStoreHeat`, `getStoredHeat`, `getMaxStoredHeat`, `storeHeat`), and `getExplosionInfluence` for blast scaling. 【F:src/main/java/ic2/api/reactor/IReactorComponent.java†L11-L23】
- [INFERRED] `processChamber`/`acceptUraniumPulse` are called every `IReactor.getTickRate()` cycle with `heatCalculation`/`damageTick` toggles to simulate asynchronous heat vs. wear. 【F:src/main/java/ic2/api/reactor/IReactorComponent.java†L11-L17】
- [DECLARED] **IReactorPlannerComponent** extends component logic with planner utilities: enumerating craftable stacks (`provideComponents`), mapping to simulated IDs, reporting affected grid slots, supported reactor types (electric/steam/universal), component categories, and statistic exports via `ReactorStat` enumerations. 【F:src/main/java/ic2/api/reactor/IReactorPlannerComponent.java†L1-L124】
- [DECLARED] Planner helper enums include `ComponentType` (indexed registry with localization keys) and `ReactorStat` (heat, energy, cooling, durability metrics). Some stats are floats, others ints, surfaced via `NumericTag`. 【F:src/main/java/ic2/api/reactor/IReactorPlannerComponent.java†L30-L124】

### Simulation scaffolding
- [DECLARED] **ISimulatedReactor** mirrors the runtime API, adding breed/fuel pulse counters, steam accounting, water consumption, production flags, and `getGameTime()` for time-based mechanics. 【F:src/main/java/ic2/api/reactor/planner/ISimulatedReactor.java†L1-L27】
- [DECLARED] **SimulatedStack** instances mirror items during planner runs: serialization (`save`/`load`), state staging (`commitState`/`reset`), `simulate` tick hooks, heat/acceptance mirrors, explosion influence, metadata (id, stats, component type). Default helpers expose `NULL_VALUE` placeholders. 【F:src/main/java/ic2/api/reactor/planner/SimulatedStack.java†L1-L33】
- [DECLARED] **BaseHeatSimulatedStack** tracks heat with a rolling `Tracker` (average/total sample, commit/reset) and clamps storage, marking stacks broken via `reactor.markBroken`. **BaseDurabilitySimulatedStack** provides similar scaffolding for damage-based parts. 【F:src/main/java/ic2/api/reactor/planner/BaseHeatSimulatedStack.java†L1-L53】【F:src/main/java/ic2/api/reactor/planner/Tracker.java†L1-L38】【F:src/main/java/ic2/api/reactor/planner/BaseDurabilitySimulatedStack.java†L1-L44】
- [DECLARED] **FloatTracker** mirrors `Tracker` for non-integer metrics (e.g., EU output averages). 【F:src/main/java/ic2/api/reactor/planner/FloatTracker.java†L1-L20】

#### Implementation checklist
- Wire every reactor tile to provide accurate heat, max heat, and HEM readings; planner tooling reuses these values directly. [DECLARED]
- Call `addOutput` each tick to accumulate EU for reporting interfaces. [DECLARED]
- Ensure `getStackInReactor`/`setStackInReactor` remain synchronous with inventory handlers used by GUIs. [DECLARED]
- Maintain slot coordinates consistent with planner grids (usually 6×9) to keep `IReactorPlannerComponent` overlays aligned. [INFERRED]
- Components must respect `heatCalculation` vs `damageTick` to avoid double-dipping on wear. [INFERRED]
- Provide meaningful `getExplosionInfluence` values so meltdown effects stack correctly. [DECLARED]
- Surface `ReactorStat` metrics for planner UI (heat, cooling, durability, etc.) even if some return zero. [DECLARED]
- For steam reactors, pipe `FluidTank` updates through Forge capabilities so heat-to-steam conversion can drain tanks. [INFERRED]

## Tiles / Tubes / Teleport
### Machine cores
- [DECLARED] **IMachine** joins `ILocation` and `IInputMachine`, exposing upgrade support (`getSupportedUpgradeTypes`, `onUpgradesChanged`), EU buffer hooks (`getAvailableEnergy`, `useEnergy`), redstone toggles, and adjacency queries for inventories (`IItemHandler`) and adjacent tubes. Machines must also reveal working state for overlays. 【F:src/main/java/ic2/api/tiles/IMachine.java†L1-L19】
- [DECLARED] **IInputMachine** reports remaining item capacity per `ItemStack`. 【F:src/main/java/ic2/api/tiles/IInputMachine.java†L1-L7】
- [DECLARED] **IEnergyStorage** inherits `IEUStorage` telemetry and adds mutators `addEnergy` / `drawEnergy` in EU units. 【F:src/main/java/ic2/api/tiles/IEnergyStorage.java†L1-L8】
- [DECLARED] **IElectrolyzerProvider**, **IFluidMachine**, **INotifiableMachine**, and related interfaces (see method catalog) specialize fluid access, progress tracking, and update hooks for GUIs. 【F:src/main/java/ic2/api/tiles/IElectrolyzerProvider.java†L1-L21】【F:src/main/java/ic2/api/tiles/IFluidMachine.java†L1-L18】
- [INFERRED] **FakePlayerMachine** / anchor helpers coordinate server-side fake player interactions for tools or automation (based on naming). 【F:src/main/java/ic2/api/tiles/FakePlayerMachine.java†L1-L45】

### Tubes & logistics
- [DECLARED] **ITube** extends `ILocation`, providing item insertion (`addItem` overloads), capability checks (`canAddItem`), neighbor validation (`canConnect`), and metadata `TubeType` (simple vs extraction). Dye colors allow routing channels. 【F:src/main/java/ic2/api/tiles/tubes/ITube.java†L1-L20】
- [DECLARED] **TransportedItem** models moving payloads: serialization (NBT/network), speed/position (0–100 progress, MIN/MAX speed), direction tracking (`setInsertionDirection`, `setExportDirection`), centering state, timeout invalidation, request IDs (UUID), and dye filters. Update loops must call `update()` to advance or time out. 【F:src/main/java/ic2/api/tiles/tubes/TransportedItem.java†L1-L214】【F:src/main/java/ic2/api/tiles/tubes/TransportedItem.java†L200-L252】
- [DECLARED] **IProviderTube** and **IRequestTube** coordinate logistics requests, referencing UUID request IDs, dye filters, and callbacks to requesters (validate amount, issue requests). Providers also expose a long `getProviderSource` for priority/unique keys. 【F:src/main/java/ic2/api/tiles/tubes/IProviderTube.java†L1-L11】【F:src/main/java/ic2/api/tiles/tubes/IRequestTube.java†L1-L21】
- [DECLARED] **ILimiterTube** constrains valid dye channels. 【F:src/main/java/ic2/api/tiles/tubes/ILimiterTube.java†L1-L8】
- [DECLARED] **IItemCache** caches item snapshots for networking; servers `registerItem` returning IDs, clients `getItem(int)` returning lazy suppliers, and both sides may `updateCache` / `clearCache`. 【F:src/main/java/ic2/api/tiles/tubes/IItemCache.java†L1-L43】
- [DECLARED] **ArrayTube** composes multiple `ITube` implementations, forwarding items round-robin (with optional looping) and forbidding transport-related queries by throwing `UnsupportedOperationException`. 【F:src/main/java/ic2/api/tiles/ArrayTube.java†L1-L38】

### Teleportation
- [DECLARED] **ITeleporterTarget** marks block entities that can send/receive teleport payloads, exposing facing, allowed transport types (`TeleportType`), and target bookkeeping (`setTarget`, `hasTarget`). `TeleportType.matches` handles entity/spawner equivalence. 【F:src/main/java/ic2/api/tiles/teleporter/ITeleporterTarget.java†L1-L28】
- [DECLARED] **TeleporterTarget** stores serialized dimension/position pairs, supports network/NBT IO, equality, and helper constructors. `getWorld` resolves the server level, `getTile` fetches the destination block entity. 【F:src/main/java/ic2/api/tiles/teleporter/TeleporterTarget.java†L1-L88】
- [DECLARED] **TargetRegistry** keeps a synchronized map of known targets to display names (non-persistent). 【F:src/main/java/ic2/api/tiles/teleporter/TargetRegistry.java†L1-L20】

#### Implementation checklist
- Keep machine energy usage synced with upgrades by recalculating after `onUpgradesChanged`. [DECLARED]
- Always expose consistent `ITube` references per side so logistics filters stay deterministic. [DECLARED]
- Update `TransportedItem` progress every tick and invalidate stalled packets to avoid ghost items. [DECLARED]
- Respect dye/channel filters in `IProviderTube` and `IRequestTube` when routing requests. [DECLARED]
- When implementing teleporters, validate `TeleportType.matches` before accepting payloads. [DECLARED]
- Use `IItemCache.registerItem` when syncing TransportedItem payloads to minimize network payload size. [DECLARED]
- For machines that spawn fake players, ensure thread-safety when performing block interactions. [INFERRED]
- Clear target registry entries when tiles unload or break to prevent stale teleport destinations. [INFERRED]

## Items / Readers / Electric
### Core item traits
- [DECLARED] **IElectricItem** defines capacity, tier, transfer limit, and `canProvideEnergy` toggles. Tiers align with energy net voltage steps. 【F:src/main/java/ic2/api/items/electric/IElectricItem.java†L1-L11】
- [DECLARED] **IElectricItemManager** orchestrates charging/discharging (with simulate flags), current charge queries, transfer limit, tool usage gating (`canUse`/`use`), armor charging, tier lookup, and tooltip generation. 【F:src/main/java/ic2/api/items/electric/IElectricItemManager.java†L1-L24】
- [DECLARED] **ElectricItem** maintains static managers: global `MANAGER`, `DIRECT_MANAGER`, backup lookups per item, optional Curios accessor, and helpers for charging armor/Curio slots and adjusting consumption by enchantments. Implementations must register managers before runtime use. 【F:src/main/java/ic2/api/items/electric/ElectricItem.java†L1-L74】
- [DECLARED] **ICustomElectricItem** lets items supply bespoke managers, while **IDamagelessElectricItem** flags items without durability loss. 【F:src/main/java/ic2/api/items/electric/ICustomElectricItem.java†L1-L7】【F:src/main/java/ic2/api/items/electric/IDamagelessElectricItem.java†L1-L6】
- [DECLARED] **IElectricEnchantable** customizes enchantment compatibility for electric gear. 【F:src/main/java/ic2/api/items/electric/IElectricEnchantable.java†L1-L11】

### Tools & scanners
- [DECLARED] **IScanner** / **IFluidScanner** supply scan radius and ore/fluid valuation callbacks; optional energy usage toggles allow preview vs actual scan. 【F:src/main/java/ic2/api/items/electric/IScanner.java†L1-L23】【F:src/main/java/ic2/api/items/electric/IFluidScanner.java†L1-L14】
- [DECLARED] **IMiningDrill** determines mining permission, optional speed boosts/extra EU cost, and consumption hooks (`onDrillUsed`). 【F:src/main/java/ic2/api/items/electric/IMiningDrill.java†L1-L18】
- [DECLARED] **IWrenchTool** modifies wrench drop loss and optionally toggles overlay rendering. 【F:src/main/java/ic2/api/items/readers/IWrenchTool.java†L1-L8】
- [DECLARED] **IWrenchable** (block-side) describes rotation/removal flows, overlay bounding boxes, drop lists, and nested `WrenchRegistry` for registering handlers for vanilla blocks. Implementations must respect player direction, shift behavior, and drop chance semantics. 【F:src/main/java/ic2/api/blocks/IWrenchable.java†L1-L170】

### Readers & upgrades
- [DECLARED] **ICropReader**, **IEUReader**, **IThermometer** expose boolean checks with static helpers to detect tool capability from an `ItemStack`. 【F:src/main/java/ic2/api/items/readers/ICropReader.java†L1-L11】【F:src/main/java/ic2/api/items/readers/IEUReader.java†L1-L11】【F:src/main/java/ic2/api/items/readers/IThermometer.java†L1-L11】
- [DECLARED] **IUpgradeItem** enumerates machine upgrade effects: type, functions, install hook, multipliers/offsets for time, speed, energy demand/storage, tier, sound, redstone inversion, tick callbacks, and recipe completion hooks (pre/post, access to drops and flags). UpgradeType describes which subsystems are touched. 【F:src/main/java/ic2/api/items/IUpgradeItem.java†L1-L73】
- [DECLARED] **ItemRegistries** centralize registries for metal armor, boxable items, coins (value-ordered), shield blockable damage sources, etc. It also exposes coin generation utilities and registration APIs. 【F:src/main/java/ic2/api/items/ItemRegistries.java†L1-L117】

#### Implementation checklist
- Register your `IElectricItemManager` (or custom manager) before items attempt to charge/discharge. [DECLARED]
- Respect `transferLimit` and `tier` checks inside `charge`/`discharge` operations; ignore-transfer-limit flags are only for internal wiring. [DECLARED]
- Update wrenchable blocks to return accurate `AABB` overlays for client previews and guard `canRemoveBlock` vs drop rate semantics. [DECLARED]
- When adding upgrades, populate all relevant multiplier/offset getters even if returning defaults. [DECLARED]
- Ensure scanners honor `useEnergy` flags so client previews do not drain charge. [DECLARED]
- Call `onDrillUsed` after successful block breaks to sync durability/charge usage. [DECLARED]
- Leverage `ItemRegistries.registerCoin` / `generateCoins` to maintain consistent coin payout ratios. [DECLARED]
- Keep reader interfaces idempotent so static helper checks remain cheap. [INFERRED]

## Network / Buffer / Container
### Manager & channels
- [DECLARED] **INetworkManager** registers `INetworkDataBuffer` types by `ResourceLocation`, manages GUI tracking, syncs tile fields (initial + incremental), relays tile events (ints or custom buffers) with `PacketRange`, and mirrors similar flows for held items. Client senders have dedicated helpers (`sendClientTileEvent`, etc.). 【F:src/main/java/ic2/api/network/INetworkManager.java†L1-L44】
- [DECLARED] **PacketRange** enumerates broadcast radii (short/long/chunk/all-dim/server) for tile events. 【F:src/main/java/ic2/api/network/tile/PacketRange.java†L1-L7】

### Data buffers
- [DECLARED] **INetworkDataBuffer** defines `write(IOutputBuffer)` / `read(IInputBuffer)` pairs; each buffer type must be registered. 【F:src/main/java/ic2/api/network/buffer/INetworkDataBuffer.java†L1-L7】
- [DECLARED] **IOutputBuffer** / **IInputBuffer** cover primitive serialization, Forge registry entries, ItemStack/FluidStack, UUID, NBT, registry keys, and `NetworkInfo.BitLevel` granular bit packing. Convenience statics help writing stacks/enums. 【F:src/main/java/ic2/api/network/buffer/IOutputBuffer.java†L1-L35】【F:src/main/java/ic2/api/network/buffer/IInputBuffer.java†L1-L33】
- [DECLARED] **NetworkInfo** annotation tags fields with bit-level compression guidance (ignore, 8–64 bits) and runtime helpers (`isValid`, `limitNumber`). 【F:src/main/java/ic2/api/network/buffer/NetworkInfo.java†L1-L49】
- [DECLARED] **EmptyDataBuffer** (see catalog) acts as a no-op placeholder for events with no payload. 【F:src/main/java/ic2/api/network/buffer/EmptyDataBuffer.java†L1-L18】

### Tile & item listeners
- [DECLARED] **INetworkFieldProvider** lists auto-synced fields for tiles (`getNetworkFields`, `getGuiFields`, optional `isDefaultData`). Implementers must ensure stable field names. 【F:src/main/java/ic2/api/network/tile/INetworkFieldProvider.java†L1-L8】
- [DECLARED] **INetworkFieldNotifier** receives sets of changed field names for both server-origin updates (`onNetworkFieldChanged`) and GUI-specific updates. 【F:src/main/java/ic2/api/network/tile/INetworkFieldNotifier.java†L1-L9】
- [DECLARED] **INetworkEventListener** and **INetworkClientEventListener** handle int-based events; the latter includes the sending player. **INetworkDataEventListener** mirrors this for custom buffers with client/server `Dist` context. 【F:src/main/java/ic2/api/network/tile/INetworkEventListener.java†L1-L5】【F:src/main/java/ic2/api/network/tile/INetworkClientEventListener.java†L1-L7】【F:src/main/java/ic2/api/network/tile/INetworkDataEventListener.java†L1-L9】
- [DECLARED] **INetworkItemEvent** / **INetworkItemBufferEvent** deliver item-bound events or buffers to specific players/hand slots, including target side metadata. 【F:src/main/java/ic2/api/network/item/INetworkItemEvent.java†L1-L9】【F:src/main/java/ic2/api/network/item/INetworkItemBufferEvent.java†L1-L9】
- [DECLARED] **IPlayerPacket** supplies helper utilities to resolve containers or find held item stacks when processing network callbacks. 【F:src/main/java/ic2/api/network/IPlayerPacket.java†L1-L26】
- [DECLARED] **IContainerDataEvent** is a lightweight hook for container-level (menu) integer syncs. 【F:src/main/java/ic2/api/network/container/IContainerDataEvent.java†L1-L5】

#### Implementation checklist
- Register every custom `INetworkDataBuffer` on mod init via `INetworkManager.registerDataBuffer`. [DECLARED]
- Populate `INetworkFieldProvider` lists with deterministic ordering so delta comparisons work. [DECLARED]
- When sending item events, use `IPlayerPacket.findPlayerStack` to locate the authoritative stack instance. [DECLARED]
- Choose `PacketRange` carefully to avoid leaking tile updates across dimensions. [DECLARED]
- Guard `onNetworkFieldChanged` handlers against client-only invocation when the player argument may be null. [INFERRED]
- Reset GUI tracking via `updateGuiField(s)` when server-side values change outside normal ticks. [DECLARED]
- Use `IOutputBuffer.writeData` with appropriate `BitLevel` to minimize network size. [DECLARED]
- Throttle item buffer events; repeated large buffers can overwhelm channel bandwidth. [INFERRED]

## Recipes / Registries
### Central registry access
- [DECLARED] **RecipeRegistry** exposes static holders for ingredient parsing, shaped craft managers, machine recipe lists (macerator, extractor, compressor, sawmill, etc.), scrap box rewards, fluid fuels, fusion recipes, can effects, potion brewing, and UU matter shapes. Many are `SidedObject` wrappers to segregate client/server registration. 【F:src/main/java/ic2/api/recipes/RecipeRegistry.java†L1-L37】

### Machine recipe lists
- [DECLARED] **IMachineRecipeList** manages `RecipeEntry` objects (id, inputs array, output, null-input flag). Helpers add simple/chance/range recipes (by `ResourceLocation`, optional NBT, XP). Input objects are converted via `RecipeRegistry.INGREDIENTS.createInputFrom`. Retrieval supports lookups by ID, matching stack, or predicate, plus removal and enumeration. 【F:src/main/java/ic2/api/recipes/registries/IMachineRecipeList.java†L1-L123】
- [DECLARED] `RecipeEntry` stores whether any `INullableInput` is present (affecting processing). 【F:src/main/java/ic2/api/recipes/registries/IMachineRecipeList.java†L87-L121】
- [DECLARED] **IAdvancedCraftingManager** (see catalog) handles shaped/shapeless registration, ore dictionary conversions, and recipe removal by key. 【F:src/main/java/ic2/api/recipes/registries/IAdvancedCraftingManager.java†L1-L44】
- [DECLARED] Specialized registries expose domain-specific hooks: e.g., **ICannerRecipeRegistry** registers fluid/item combos, **IElectrolyzerRecipeList** maps fluids to outputs/energy cost, **IFusionRecipeList** handles multi-input EU-intensive recipes, **IFluidFuelRegistry** enumerates burnable fluids with EU output. (See method catalog for method lists.)
- [DECLARED] **IIngredientRegistry** converts arbitrary objects (item stacks, tags, custom wrappers) into `IInput` abstractions and supports caching. (Detailed methods in catalog.)
- [DECLARED] **IUUMatterRegistry** returns shape IDs and `NonNullList` outputs for UU crafting; keyed by dimension (via `SidedObject`).

### Recipe flags & misc
- [DECLARED] `recipes.misc.RecipeFlags` enum defines boolean/float flags applied to recipe outputs (heat usage, fluid rate, etc.), enabling planner overlays. 【F:src/main/java/ic2/api/recipes/misc/RecipeFlags.java†L1-L80】
- [DECLARED] Queue APIs (under `ingridients.queue`) expose asynchronous recipe processing semantics (IStackOutput, etc.), ensuring machine outputs can be scheduled. (See catalog.)

#### Implementation checklist
- Initialize `RecipeRegistry.INGREDIENTS` before any machine tries to convert inputs. [DECLARED]
- Register recipes via provided helpers to ensure consistent `RecipeEntry` creation and null-input detection. [DECLARED]
- Use `SidedObject#get` correctly: server registrations should run on the logical server thread only. [DECLARED]
- When adding removal logic, target recipes by `ResourceLocation` to avoid collateral deletions. [DECLARED]
- Supply XP, chance, and range metadata where appropriate so downstream GUIs can display production stats. [DECLARED]
- Keep custom ingredient converters thread-safe if they cache inputs. [INFERRED]
- For queue-based outputs, emit `IStackOutput` in deterministic order to match auto-ejection expectations. [INFERRED]
- Document custom recipe flags and honor them in machines that inspect `CompoundTag` recipe data. [INFERRED]

## Events
- [DECLARED] **FoamEvent.Check** fires before scaffolding/foam placement; listeners can override target type or cancel. **FoamEvent.Place** allows requesting forced foam placement or cancellation. TargetType enumerates structural categories (scaffold, cable, tube, pipe, custom). 【F:src/main/java/ic2/api/events/FoamEvent.java†L1-L67】
- [DECLARED] **LaserEvent** (and subclasses) fire for laser tool actions: `LaserShootEvent` (item firing), `LaserExplodeEvent` (explosion parameters), `LaserEntityHitEvent` (entity collisions, pass-through toggle), `LaserBlockHitEvent` (block impact, drop chance). All are cancelable to let mods modify range/power/drops. 【F:src/main/java/ic2/api/events/LaserEvent.java†L1-L70】
- [DECLARED] **RetextureEvent** notifies when painters attempt to apply block textures; exposes position, side, player, texture container (block state, rotations, colors). Listeners can mark the event as applied or mutate texture data. 【F:src/main/java/ic2/api/events/RetextureEvent.java†L1-L83】
- [DECLARED] **ScrapBoxEvent** triggers when scrap boxes roll drops, with variants for player use (`ScrapBoxPlayerUseEvent`) and dispenser usage (`ScrapBoxDispenseEvent`). Listeners can inspect/replace drop lists. 【F:src/main/java/ic2/api/events/ScrapBoxEvent.java†L1-L44】
- [DECLARED] **ArmorSlotEvent** announces available module slots for armor pieces, allowing listeners to grant additional module capacity per `ModuleType`. 【F:src/main/java/ic2/api/events/ArmorSlotEvent.java†L1-L33】

#### Implementation checklist
- Subscribe to foam events to whitelist additional blocks/cables before foam auto-placement occurs. [DECLARED]
- Adjust laser event parameters (power, block breaks, pass-through) to integrate protective shields or alternate drop logic. [DECLARED]
- Use `RetextureEvent` to veto or customize painter applications on custom blocks. [DECLARED]
- When modifying scrap box drops, replace the `List<ItemStack>` in-place to keep dispenser logic consistent. [DECLARED]
- Update armor module slot counts during `ArmorSlotEvent` with `addSlots`, but clamp totals (API enforces max of 9). [DECLARED]
- Remember to respect cancelable flags; returning without calling `setApplied(true)` or `requestFoamPlacement()` leaves behavior unchanged. [INFERRED]

