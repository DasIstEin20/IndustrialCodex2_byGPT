# API Behavior Map

## Energy/Cables

### ic2.api.energy.IEnergyNet
* `IEnergyTile getTile(Level world, BlockPos pos)` / `getSubTile` / `getTiles` — look up the main and attached grid tiles for a position (multi-block aware).
* `void addTile(IEnergyTile tile)` / `removeTile` / `updateTile` — register and maintain energy participants in the network graph.
* `int getPowerFromTier(int tier)` / `getTierFromPower(int power)` / `String getDisplayTier(int tier)` — translate between EU packet power and tier display strings.
* `TransferStats getStats(IEnergyTile tile)` / `List<PacketStats> getPacketStats(IEnergyTile tile)` — query aggregate and per-packet EU throughput for diagnostics.

### ic2.api.energy.tile core contracts
* `IEnergyTile` extends `ILocation`; implementers must return the hosting world and position.
* `IEnergyAcceptor` → `boolean canAcceptEnergy(IEnergyEmitter emitter, Direction side)` — whitelist sides and partner tiles that may inject EU.
* `IEnergyEmitter` → `boolean canEmitEnergy(IEnergyAcceptor acceptor, Direction side)` — gate packet emission toward adjacent acceptors.
* `IEnergySink` → `int getSinkTier()`, `int getRequestedEnergy()`, `int acceptEnergy(Direction side, int amount, int voltage)` — advertise safe tier (EU per packet), request amount for the next tick, and consume delivered EU returning leftovers. Implementers must handle per-side input.
* `IEnergySource` → `int getSourceTier()`, `int getMaxEnergyOutput()`, `int getProvidedEnergy()`, `void consumeEnergy(int consumed)`, `default void onPacketFailed()` — expose outgoing EU packet size, available buffer, and deduct energy when the net successfully routes a packet; react when a transmission failed. `SourceType` enum categorises behaviour (always-on, passive, intelligent, etc.) and includes helper combinators (`merge`, `required`).
* `IMultiEnergySource` adds `boolean hasMultiplePackets()` and `int getPacketCount()` for emitters that can push several packets per tick.
* `IMultiEnergyTile` exposes subordinate `IEnergyTile` instances (e.g., transformers with sub-nodes).
* `IEnergyConductor` merges acceptor/emitter roles and adds cable durability hooks: insulation checks (`isWaterlogged`, `isLavaLogged`), loss figures (`getConductionLoss`), insulation limits (`getInsulationEnergyAbsorption`, `getInsulationBreakdownEnergy`), and breakdown thresholds (`getConductorBreakdownEnergy`). Maintenance methods (`removeInsulation`, `removeConductor`) allow wrench tools to degrade cables.
* `IEnergyConductorAnchored` requires an `IAnchorTile` anchor implementation for cables clamped in space; `IEnergyConductorColored` exposes dye metadata; `IEnergyConductorModifiable` adds mutators (`tryAddInsulation`, `tryRemoveInsulation`).

### ic2.api.energy.impl helpers
* `LinkedSink` and `LinkedSource` wrap arbitrary world/position pairs as lightweight acceptor/emitter facades for sub-tiles. They proxy `getWorldObj`, `getPosition`, and directional capability checks back to the underlying tile logic.

**Implementation Checklist**
- Implement per-side EU negotiation: advertise tiers, request amounts, and honour `canAcceptEnergy`/`canEmitEnergy` checks.
- Feed every participating tile into `IEnergyNet#addTile/removeTile` when loading, unloading, or changing state.
- Convert between tier and packet size using `IEnergyNet` helpers to prevent overvoltage damage.
- Track outgoing packets (`getProvidedEnergy`, `consumeEnergy`) and recover from failed sends via `onPacketFailed`.
- For conductors, respect insulation/waterlogging rules and expose maintenance hooks for wrenches and anchors.
- Multi-source tiles must report packet counts consistently to avoid duped EU.
- Ensure all `ILocation` implementations return stable world/position references even for virtual sub-tiles.

## Reactor/Planner

### Core reactor contracts (`ic2.api.reactor`)
* `IReactor` (extends `ILocation`) defines the per-tick simulation surface:
  * Heat lifecycle: `getHeat`, `setHeat`, `addHeat`, `getMaxHeat`, `setMaxHeat`, `getHeatEffectModifier`, `setHeatEffectModifier`.
  * Energy/steam bookkeeping: `double getEnergyOutput()`, `void addOutput(float)`, `boolean isProducingEnergy()`, `int getTickRate()`.
  * Inventory grid: `ItemStack getStackInReactor(int x, int y)` / `setStackInReactor` for the component matrix (commonly 6×9 with extra chambers); `explode()` to trigger catastrophic failure.
* `IChamberReactor` augments `IReactor` with geometry (`int getWidth()`, `int getHeight()`) and `refreshChambers()` when chambers attach/detach.
* `IReactorChamber` exposes the master reactor reference; `ISteamReactorChamber` tags chambers specific to steam reactors.
* `ISteamReactor` adds accessors for coolant and steam buffers (`FluidTank getWaterTank()`, `getSteamTank()`), signalling water/steam EU conversions.
* `IReactorProduct` marks items that can sit in the reactor; `boolean isValidForReactor(ItemStack, IReactor)` vets placement.
* `IReactorComponent` extends `IReactorProduct` with the tick contract: `processChamber` (regular heat/damage tick), `acceptUraniumPulse` (neutron interactions), heat storage operations (`canStoreHeat`, `getStoredHeat`, `getMaxStoredHeat`, `storeHeat` returning overflow), and explosion influence weighting.
* `IUsableUranium` identifies spent fuel logic via `ItemStack createDepletedUraniumRod()`.

### Planner and simulation (`ic2.api.reactor.planner`)
* `IReactorPlannerComponent` adds planner-centric metadata:
  * Inventory helpers (`applyStackSize`, `getStackSize`, `provideComponents` to populate planner palettes).
  * Identification (`short getComponentID`, `SimulatedStack createSimulationComponent`).
  * UI support (`addToolTip`, `addAffectedSlots`).
  * Categorisation (`ReactorType` ELECTRIC/STEAM/UNIVERSAL, `ComponentType` enumerations for rods, vents, exchangers, etc.).
  * Stat exposure: `List<ReactorStat> getStats`, `NumericTag getReactorStat(ReactorStat, ItemStack[, IReactor planner, int x, int y])`. `ReactorStat` enumerates planner metrics (heat production, EU/t, coolant usage, durability, etc.) with typed storage.
* `ISimulatedReactor` mirrors the in-game reactor for the planner:
  * Component access (`SimulatedStack getItem(int x, int y)`, `markBroken`).
  * Heat/steam lifecycle identical to `IReactor`, plus `addSteam`, `consumeWater`, `isSteamReactor`, `isSimulatingPulses`, `long getGameTime()`.
  * Pulse counters (`addBreedingPulse`, `addFuelPulse`).
* `SimulatedStack` abstracts simulated item stacks:
  * Persistence hooks (`syncStack`, `save`, `load`, `commitState`, `reset`).
  * Tick hooks (`simulate`, `acceptUraniumPulse`, heat storage operations mirroring `IReactorComponent`).
  * Metadata (`short getId`, `List<ReactorStat> getStats`, `ReactorType getValidType`, `ComponentType getComponentType`, `NumericTag getStat`).
* `BaseHeatSimulatedStack` / `BaseDurabilitySimulatedStack` implement `SimulatedStack` with built-in heat or durability tracking, including a `Tracker` helper (averages cumulative changes) to monitor component degradation.
* `Tracker` collects counts/averages of state changes for planner analytics (`addChange`, `commit`, `reset`, `getAverage`, `getTotal`).

**Implementation Checklist**
- Maintain consistent reactor heat math: `storeHeat` must clamp to `getMaxStoredHeat` and report overflow for hull damage.
- Expose the full grid via `getWidth`/`getHeight` so planners know available slot coordinates.
- For components, implement both normal ticks and uranium pulse handling to interact with adjacent cells properly.
- Populate planner metadata (`ComponentType`, `ReactorStat`) to drive UI highlighting and stat readouts.
- Steam reactors must back coolant/steam tanks with Forge `FluidTank` instances honoring planner queries.
- `SimulatedStack` implementations should persist state via NBT tags and revert with `reset()` for iterative simulations.
- Call `markBroken` when simulated items exceed limits so the planner can visualise failures.
- Use `Tracker` or equivalent to report average heat/damage rates for planner overlays.

## Tiles/Tubes/Teleport

### Machine and storage interfaces (`ic2.api.tiles`)
* `IMachine` (extends `ILocation`, `IInputMachine`) governs machine blocks: upgrade support (`EnumSet<UpgradeType> getSupportedUpgradeTypes`, `onUpgradesChanged`), energy draw (`int getAvailableEnergy`, `boolean useEnergy(int toUse, boolean doUse)`), work state (`boolean isMachineWorking`), redstone gating (`setRedstoneSensitive`, `isRedstoneSensitive`), and adjacent IO discovery (`IItemHandler getConnectedInventory(Direction)`, `ITube getConnectedTube(Direction)`).
* `IInputMachine` marks machines with sided item inputs via `Direction` flags and slot checks (see source for detailed methods).
* `INotifiableMachine` expects GUI sync hooks (`void onGuiClosed`, etc.) for remote viewers.
* `IEnergyStorage` (extends reader `IEUStorage`) adds mutable storage: `int addEnergy(int power)`, `int drawEnergy(int power)` returning leftover/removed EU.
* `IElectrolyzerProvider` exposes `IEnergyStorage getEnergyStorage()` and fluid IO for electrolyzers.
* `IRecipeMachine` gives recipe context: `boolean acceptsRecipeOutput()`, `void onRecipeComplete()` (see source for specifics).
* `IFluidMachine` exposes Forge fluid capability wrappers for machine sides.
* `ITerraformer` returns pattern data for terraformers: `BlockPos getNextTarget()`, etc. (review file for exact behaviour if used).
* `ICopyableSettings` supplies methods to copy machine configuration between block entities (`saveSettings`, `loadSettings`).
* `IAnchorTile` references anchor components for cables/tubes.

### Display and reader contracts (`ic2.api.tiles.display`, `.readers`)
* Display interfaces (`IDisplayInfo`, `IDisplayRegistry`, `IMonitorRenderer`) feed HUD/monitor tiles with formatted `Component` lines, register renderers, and draw monitors with partial tick interpolation.
* Reader probes expose telemetry: `IActivityProvider` (work progress), `IEUProducer`, `IEUStorage`, `IProgressMachine`, `ISubProgressMachine`, `ISpeedMachine`, `IFuelStorage`, `IPumpTile`, `IAirSpeed`, `IWorkProvider`. Each interface provides getters for stored energy, production rates, fluid levels, etc., enabling reader items to pull machine stats.

### Tubes (`ic2.api.tiles.tubes`)
* `ITube` handles transported items through tubes: `addItem(ItemStack, Direction, DyeColor)`, `addItem(TransportedItem, Direction)`, `boolean canAddItem(TransportedItem, Direction)`, `boolean canConnect(ITube other, Direction)`, `TubeType getTubeType()` (SIMPLE or EXTRACTION). Implements `ILocation` for world context.
* `IItemCache` caches item IDs for network sync; `ILimiterTube`, `IProviderTube`, `IRequestTube` define logistics behaviours (rate limiting, provisioning, requesting).
* `TransportedItem` serialises tube payloads for networking (`read/write(IInputBuffer/IOutputBuffer)`, `serializeEssentials`, speed/progress setters, colour tagging, request IDs). It enforces speed bounds (`MIN_SPEED`, `MAX_SPEED`) and supports `UUID` logistics tracking.

### Teleport targets (`ic2.api.tiles.teleporter`)
* `ITeleporterTarget` describes teleport endpoints: `boolean isInterdimensional()`, `BlockPos getTargetPos()`, `float getTargetYaw()`, `boolean canTeleport(Player)` (see file for detailed behaviour), plus cost modifiers for EU usage.

**Implementation Checklist**
- Honour Forge capability threading rules when exposing energy, item, or fluid handlers from machines and tubes.
- Keep machine state persistent via `saveSettings`/`loadSettings` and ensure network sync for GUI fields provided by display interfaces.
- Enforce upgrade limits and call `onUpgradesChanged` when inventory modifiers change.
- When interacting with tubes, validate connection compatibility and respect dye/request metadata to avoid routing loops.
- Teleporter targets must validate destination safety (`canTeleport`) and report yaw/pos accurately for arriving entities.
- Reader providers should return up-to-date metrics each tick for scanners and monitors.
- Maintain EU accounting in `IEnergyStorage` implementations to avoid duping or negative energy states.
- When serialising transported items, keep `TransportedItem` IDs unique and ensure `deserializeEssentials` matches write order.

## Items/Readers/Electric

### General item contracts (`ic2.api.items`)
* `IAutoEatable` — auto-consumable food items (`boolean canAutoEat(ItemStack)`, `int getAutoEatInterval()` etc.).
* `IBoxableItem` — determines if items can be boxed/stored; includes `boolean canBeStored(ItemStack)`.
* `ICoinItem` — coins expose values and wallet integration.
* `ICutterItem` — sheet metal cutters supply `int getMaxDamage()` and behaviour when cutting cables.
* `IDisplayProvider` — items providing HUD text lines.
* `IDrinkContainer` — re-usable drink items with `ItemStack getEmptyContainer(ItemStack)`.
* `IFoamOverrider` — items altering foam behaviour (e.g., scaffolds) via `FoamEvent.TargetType getFoamTarget(ItemStack)`.
* `IFuelableItem` — burnable items specify `int getFuelValue(ItemStack)` and `boolean canBurn(ItemStack)`.
* `IRepairable` — items responding to `repair` actions.
* `ITagItem`/`ITagBlock` — items that expose extra tooltip tags about their target block/item.
* `ITerraformerBP` — blueprint items describe terraform patterns (`BlockPos[] getPattern()`).
* `IUpgradeItem` — machine upgrade cards: `EnumSet<UpgradeType> getTypes`, `boolean canApplyTo(IMachine)`, `void onAdded/Removed`, `void tickUpgrade`. Nested `UpgradeType` enumerates transformer, energy, etc. with tier metadata.
* `IWindmillBlade` — blades provide area, wind resistance, and damage thresholds for kinetic generators.

### Armor modules (`ic2.api.items.armor`)
* `ICustomArmor`/`IMetalArmor` define damage reduction, special overlays, and forging bonuses.
* `IArmorModule` exposes module install/removal hooks and energy/tick usage (`onArmorTick`, `onEntityAttacked`, etc.), grouped by `ModuleType` (JETPACK, ENERGY_SHIELD, etc.).
* `IArmorHud` — supply HUD components; `IFoamSupplier` — provide foam for armor-based foam launchers.
* `IEnergyShieldArmor` — exposes shield capacity and drain per hit.

### Electric tools (`ic2.api.items.electric`)
* `IElectricItem` — base electric item stats (capacity, tier, transfer limit, whether it can provide energy).
* `IElectricItemManager` — core charge/discharge contract used by the energy network (`charge`, `discharge`, `getCharge`, `canUse`, `use`, `chargeFromArmor`, etc.), supporting simulation flags and ignoring transfer limits.
* `ICustomElectricItem` — override manager retrieval (`IElectricItemManager getManager`), custom charge bars, and EU consumption per use.
* `IDamagelessElectricItem` — electric items that avoid durability loss when unpowered.
* `IElectricEnchantable` — controls compatibility with enchantments and the `EnchantPower` scaling.
* `IFluidScanner` / `IScanner` — scanning devices returning scan times, consumed EU, and results (`Component getTargetInfo`, `int startScan(Level, BlockPos)` etc.).
* `IMiningDrill` — drills define mining tiers, energy per operation, upgrade hooks, and allowed block tags.

### Readers (`ic2.api.items.readers`)
* `ICropReader`, `IEUReader`, `IThermometer` — items that display crop stats, EU storage, or temperature, typically hooking into tile reader interfaces.
* `IWrenchTool` — wrench items adjust lossless chance overlays: `double getActualLoss(ItemStack stack, double originalLoss)` and `boolean shouldRenderOverlay`.

### Block interaction (`ic2.api.blocks.IWrenchable`)
* Supplies full wrench interaction schema: facing queries (`getFacing`), permission checks (`canSetFacing`, `canRemoveBlock`), state changes (`setFacing`, `doSpecialAction`), overlay hitboxes (`hasSpecialAction`), drop logic (`getDropRate`, `getDrops`).
* Nested `WrenchRegistry` allows registering `IWrenchable` handlers for vanilla blocks, providing default behaviour for pistons, stairs, hoppers, etc.

**Implementation Checklist**
- Electric items must expose consistent tier/capacity so `IElectricItemManager` can enforce EU transfer limits.
- Tool items implementing scanners or drills should deduct EU via the manager and respect scan durations/cooldowns.
- Wrench tools must cooperate with `IWrenchable` to honour drop rates and overlay visuals.
- Upgrade items should verify compatibility with machine upgrade slots and call `onAdded/onRemoved` appropriately.
- Armor modules should track per-slot module counts using `ArmorSlotEvent` data and cap entries at nine modules.
- Reader items rely on tile reader interfaces; ensure target tiles implement corresponding telemetry contracts.
- Blueprint/terraformer items must deliver deterministic pattern data for world edits.
- Fuelable or foam-supplying items should synchronise with relevant events (`FoamEvent`, fuel registry) for consistent behaviour.

## Network/Buffer/Container

### Buffer primitives (`ic2.api.network.buffer`)
* `IInputBuffer`/`IOutputBuffer` — endian-safe serializers for packets. Support primitives (`readInt`, `writeInt`), varints, bit-level reads (`readData(BitLevel)`), NBT (`readNBTData`), Forge registry entries (`readForgeRegistryEntry`), item/fluid stacks, UUIDs, and registry keys.
* `INetworkDataBuffer` — mark objects that can serialise themselves via the buffer pair (`void read(IInputBuffer)`, `void write(IOutputBuffer)`), used by `TransportedItem` and other sync payloads.
* `IBitLevelOverride` — allow packets to temporarily change compression bit depth.

### Network coordination (`ic2.api.network`)
* `INetworkManager` handles channel lifecycle: `void init()`, `void register(int id, Class<? extends IPlayerPacket> type)`, `void sendTo(IPlayerPacket packet, ServerPlayer player)`, `void sendToTracking`, `void sendToServer`, `void addListener(INetworkEventListener listener)`, etc. Maintains one logical channel for IC2 packets.
* `IPlayerPacket` — base interface for packets: `void encode(IOutputBuffer)`, `void decode(IInputBuffer)`, `void handle(ServerPlayer)`/`handleClient(LocalPlayer)`.

### Tile listeners (`ic2.api.network.tile`)
* `INetworkEventListener` — generalised tile event handling with `void onNetworkEvent(int id, IInputBuffer data)`.
* `INetworkClientEventListener` / `INetworkDataEventListener` — client-specific event and data change callbacks for block entities.
* `INetworkFieldProvider` — list fields to sync by name (`getNetworkFields`, `getGuiFields`, `default boolean isDefaultData`).
* `INetworkFieldNotifier` — notify watchers when a field changes (`void addNetworkFields(List<String>)`, etc.).

### Container sync (`ic2.api.network.container` & `.item`)
* `IContainerDataEvent` — containers deliver integer updates via `onDataReceived(int key, int value)`.
* `INetworkItemEvent` / `INetworkItemBufferEvent` — item containers respond to updates broadcast over the network (e.g., equipment sync) with payload buffers.

**Implementation Checklist**
- Serialise all packet payloads through `IInputBuffer`/`IOutputBuffer` to maintain protocol compatibility and varint framing.
- Register packet classes with unique IDs via `INetworkManager#register` and ensure handlers respect logical side (client vs server).
- Use `INetworkFieldProvider` to declare block entity fields that need periodic sync and fire `INetworkFieldNotifier` when values change.
- Container menus should funnel integer updates through `IContainerDataEvent` for vanilla-friendly syncing.
- Tile listeners must be thread-aware: handle events on the main server thread where world access occurs.
- When streaming item data, rely on `INetworkDataBuffer` to avoid duplicating serialisation code.
- Keep protocol bit-level overrides balanced (restore defaults after temporary compression changes).
- Document channel versioning alongside your packet registration to avoid mismatched clients.

## Recipes/Registries

### Ingredient model
* `IInput`/`INullableInput` — abstract recipe ingredient matchers. `INullableInput` flags optional inputs for machines that accept empty slots.
* `IOutputGenerator` — lazily produce outputs (items/fluids) at runtime given context.
* `IRecipeOutput`, `IRecipeOutputChance`, `IFluidRecipeOutput` — describe deterministic, probabilistic, and fluid results. Provide methods to materialise results (`List<ItemStack> getOutputs`, `float getChance`, etc.).
* `IStackOutput` — wrappers for outputting stacks into inventories or tanks.
* `ICanEffect` — register additional recipe effects (sounds, particles) triggered when a recipe completes.

### Registry suite (`ic2.api.recipes.registries`)
* `IListenableRegistry<T>` — base for registries that support change listeners (`void addListener`, `void removeListener`, `void notifyListeners`).
* `IMachineRecipeList` — central processing queue: add/remove recipes (`addRecipe`, `removeRecipe`), query by `ResourceLocation` or predicate, convert convenience inputs (`convertInputs`), and handle XP/chance/range outputs via helper methods. `RecipeEntry` stores ID, inputs, output, and null-input flags.
* `IAdvancedCraftingManager` — manage crafting grid recipes beyond vanilla (pattern storage, `boolean addRecipe`, `removeRecipe`).
* `ICannerRecipeRegistry`, `IElectrolyzerRecipeList`, `IFusionRecipeList`, `IRecyclerRecipeList`, `IRefiningRecipeList` — machine-specific registries with getters for recipe entries and removal hooks; typically expose metadata such as required heat or catalysts.
* `IFluidFuelRegistry` — register fluids as generator fuels with burn times and EU/t output.
* `IFoodCanRegistry` — store canned food compositions and healing values.
* `IPotionBrewRegistry` — map brewing inputs to potion outputs for IC2 machines.
* `IRareEarthRegistry` — register rare earth outputs from mining or scrap processing.
* `IScrapBoxRegistry` — manage scrapbox loot pools with weights and categories.
* `IUUMatterRegistry` — register UU-matter templates linking inputs to generated stacks.
* `IIngredientRegistry` — central factory to convert arbitrary objects (`ItemStack`, `TagKey`, etc.) into `IInput` implementations.
* `IRecipeFilter` — predicate hooks to test recipe eligibility (`boolean test(ResourceLocation id, RecipeEntry entry)`).

### Queue helpers (`ic2.api.recipes.ingridients.queue`)
* `IInputter` — consumes inputs from machine inventories respecting sidedness and filter constraints.
* `IStackOutput` — deposit outputs back into target inventories or buffers, handling partial insertion.

**Implementation Checklist**
- Register recipes with stable `ResourceLocation` IDs and use helper methods (`addSimpleRecipe`, `addChanceRecipe`) for common patterns.
- Convert external ingredient descriptors through `IIngredientRegistry` to keep matcher implementations consistent.
- When adding nullable inputs, ensure machine logic can handle missing stacks (`hasNullInput` flag in `RecipeEntry`).
- Listen for registry changes via `IListenableRegistry` if machines cache recipes in memory.
- Fluid fuel and UU-matter registries should validate energy values to avoid exploits.
- Provide removal hooks (`removeRecipe`) when datapacks or scripts adjust recipes at runtime.
- Recipe outputs must implement `IRecipeOutput` correctly so XP, chance, and range values propagate to GUIs.
- Use `IStackOutput` helpers to avoid item loss when inventories are full mid-process.

## Events

### ArmorSlotEvent
* Fired when armour module slots are being tallied. Provides the armour `Item`, string identifier, `EquipmentSlot`, and mutable `Object2IntMap<ModuleType>`. Call `addSlots` to grant additional module capacity (capped at nine per type).

### FoamEvent
* Base foam placement event extending `LevelEvent` with target position/state. Subclasses:
  * `FoamEvent.Check` (Cancelable) — determine whether foam may be applied, optionally override `TargetType` (ANY/SCAFFOLD/CABLE/TUBE/PIPE/CUSTOM).
  * `FoamEvent.Place` (Cancelable) — triggered before placement; call `requestFoamPlacement()` to force foam deposition and `shouldPlaceFoam()` to check request status.

### LaserEvent
* General laser firing event (Cancelable) containing emitter `Entity`, source `LivingEntity`, range, power, block break count, explosion/smelt flags. Variants fire at different lifecycle stages:
  * `LaserShootEvent` — just before the laser is fired; includes held `ItemStack`.
  * `LaserExplodeEvent` — when an explosive laser detonates; exposes explosion power/drop rate.
  * `LaserEntityHitEvent` — when a laser hits an entity; set `passThrough` to allow continuing.
  * `LaserBlockHitEvent` — when hitting a block; can toggle removal/drop behaviour and adjust drop chance.

### RetextureEvent
* Raised during painter/spray retexturing. Supplies world position, clicked side, applying player, and a mutable `TextureContainer` describing the new texture (state, side, rotations, colours). `setApplied(true)` confirms the change.

### ScrapBoxEvent
* Fired when a scrap box rolls loot. Exposes mutable drop list and the scrap box stack. Variants distinguish triggers:
  * `ScrapBoxPlayerUseEvent` — player right-click consumption (includes `Player`, `InteractionHand`).
  * `ScrapBoxDispenseEvent` — dispenser activation (includes `BlockSource`).

**Implementation Checklist**
- Post events on the Forge event bus and respect cancelable semantics (`isCanceled`) before applying world changes.
- Populate mutable payloads (drop lists, foam types, texture containers) before listeners inspect them.
- Ensure listeners run on the main thread, especially when modifying world state or tile entities.
- Use provided helper methods (`requestFoamPlacement`, `addSlots`) instead of mutating internals directly.
- Document which items or machines trigger each event so mod integrators can hook appropriately.
- When firing custom laser events, keep range/power consistent with damage calculations to avoid desyncs.
- Preserve existing drop/texture data if an event is cancelled to avoid partial updates.
- For scrap box events, update both player and dispenser contexts to allow achievements or statistics tracking.
