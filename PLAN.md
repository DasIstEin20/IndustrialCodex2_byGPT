# Forge 1.20.1 Migration Plan

## Stage S1 – Audit & Inventory

- [x] **T001** – Document build tooling baseline (_docs_)
  - Targets: (docs only)
  - Description: Summarize current ForgeGradle/Forge/mapping versions and Java toolchain state in PLAN.md for migration context.
  - Acceptance criteria:
    - PLAN.md captures Gradle, Forge, mapping, and Java versions in use today.
    - Identified upgrade gaps feeding into Stage S2 tasks.
  - Findings:
    - Gradle wrapper pinned to **7.5** via `gradle/wrapper/gradle-wrapper.properties`.
    - `build.gradle` uses **ForgeGradle 5.1.+** with **Forge 1.19.2-43.1.47** and **official 1.19.2 mappings**.
    - Java toolchain already targets **Java 17**, matching the Minecraft 1.18+ baseline.
    - Stage S2 tasks must lift wrapper to Gradle 8.x, adopt ForgeGradle 6, and switch to Mojang+Parchment mappings for 1.20.1.

- [ ] **T002** – Document source layout and entrypoint gaps (_docs_) 
  - Targets: (docs only)
  - Description: Map current source tree, note absence of gameplay packages and @Mod entrypoint, and record implications for migration.
  - Acceptance criteria:
    - PLAN.md lists existing packages under src/main/java and highlights missing runtime module.
    - Follow-up tasks reference canonical package names for new runtime scaffolding.

- [ ] **T003** – Catalog registries & missing content (_docs_) 
  - Targets: (docs only)
  - Description: List expected block/item/block entity/menu/recipe/sound registries based on API and lang files, noting missing implementations.
  - Acceptance criteria:
    - PLAN.md enumerates registry domains requiring DeferredRegister rebuilds.
    - Gaps mapped to specific Stage S3/S9 tasks.

- [ ] **T004** – Review networking API expectations (_docs_) 
  - Targets: (docs only)
  - Description: Summarize INetworkManager responsibilities and data buffer usage to guide SimpleChannel migration.
  - Acceptance criteria:
    - PLAN.md captures packet categories (tile sync, gui, item) and required features.
    - Stage S5 tasks reference this audit for packet coverage.

- [ ] **T005** – Review config expectations (_docs_) 
  - Targets: (docs only)
  - Description: Document legacy config lifecycle described by API, identify mapping to ForgeConfigSpec tiers.
  - Acceptance criteria:
    - PLAN.md captures config phases (loadConfigs/preInit/postInit) and migration needs.
    - Stage S7 tasks mapped to address config lifecycle.

- [ ] **T006** – Assess capability usage points (_docs_) 
  - Targets: (docs only)
  - Description: List capabilities exposed via IC2Classic (tubes, notifiable machines, armor) and note missing attachment hooks.
  - Acceptance criteria:
    - PLAN.md enumerates required capability tokens/providers.
    - Stage S6 tasks planned for each capability.

- [ ] **T007** – Audit data assets and datagen needs (_docs_) 
  - Targets: (docs only)
  - Description: Record present assets (lang only) and missing blockstates/models/loot/tags to scope datagen rebuild.
  - Acceptance criteria:
    - PLAN.md documents asset gaps per domain.
    - Stage S8 datagen tasks referenced to fill each gap.

- [ ] **T008** – Identify client-only hooks (_docs_) 
  - Targets: (docs only)
  - Description: List API references needing Dist.CLIENT gating (renderers, particles, keybinds) for future migration.
  - Acceptance criteria:
    - PLAN.md lists client-only systems for Stage S4 follow-up.
    - Notes capture any missing classes requiring recreation.

- [ ] **T009** – Spot legacy/oversized API classes (_docs_) 
  - Targets: (docs only)
  - Description: Flag API classes likely needing refactor or wrappers to avoid monolithic implementations in new runtime.
  - Acceptance criteria:
    - PLAN.md highlights candidate classes/packages to split or wrap.
    - Stage S9 tasks reference mitigation strategies.


## Stage S2 – Build System Baseline

- [ ] **T020** – Upgrade Gradle wrapper to 8.x (_build_) 
  - Targets: gradle/wrapper/gradle-wrapper.properties
  - Description: Point Gradle wrapper to 8.x distribution supporting ForgeGradle 6 and Java 17.
  - Acceptance criteria:
    - Gradle wrapper references 8.x distribution URL.
    - Wrapper scripts regenerate without manual edits.

- [ ] **T021** – Update build.gradle for Forge 47.x & ForgeGradle 6 (_build_) 
  - Targets: build.gradle
  - Description: Adopt ForgeGradle 6 plugin DSL, bump Forge dependency to 1.20.1-47.x, and switch to Mojang+Parchment mappings.
  - Acceptance criteria:
    - build.gradle uses net.minecraftforge.gradle 6.x and Forge 47.x coordinates.
    - Mappings configured for Mojang+Parchment 1.20.1.

- [ ] **T022** – Refresh gradle.properties for Gradle 8 defaults (_build_) 
  - Targets: gradle.properties
  - Description: Normalize gradle.properties with org.gradle warnings, memory flags, and Java 17 toolchain hints.
  - Acceptance criteria:
    - gradle.properties cleaned of legacy FG flags and includes useful defaults.
    - Settings align with Gradle 8 recommendations (warnings-as-errors optional toggle).

- [ ] **T023** – Add mods.toml and pack metadata (_build_) 
  - Targets: (docs only)
  - Description: Create Forge 1.20.1 compliant META-INF/mods.toml and pack.mcmeta referencing IndustrialCodex identifiers.
  - Acceptance criteria:
    - mods.toml present with correct loader version range and mod metadata.
    - pack.mcmeta updated for pack_format 15+.

- [ ] **T024** – Update run configurations for ic2 namespace (_build_) 
  - Targets: build.gradle
  - Description: Replace examplemod run config namespaces with ic2, refresh datagen args, and ensure logging markers remain useful.
  - Acceptance criteria:
    - Run configs reference ic2 mod id for client/server/gameTest/data.
    - Data run points to src/generated/resources and uses new mod id.

- [ ] **T025** – Expand settings.gradle repositories (_build_) 
  - Targets: settings.gradle
  - Description: Add Parchment and other required plugin repositories to pluginManagement for ForgeGradle 6.
  - Acceptance criteria:
    - settings.gradle lists parchment maven and additional plugin repos as needed.
    - Ensures Gradle sync succeeds post-upgrade.


## Stage S3 – Core Mod Init & Registries

- [ ] **T030** – Create IndustrialCodex mod entrypoint (_code_) 
  - Targets: src/main/java/ic2/IndustrialCodex.java
  - Description: Add @Mod class wiring mod event bus, forge event bus, and initial logging.
  - Acceptance criteria:
    - @Mod annotated entrypoint exists under ic2 namespace.
    - Constructor registers listeners on mod event bus without deprecated APIs.

- [ ] **T031** – Introduce IC2Constants (_code_) 
  - Targets: src/main/java/ic2/core/IC2Constants.java, src/main/java/ic2/IndustrialCodex.java
  - Description: Centralize mod id, logger, and resource helpers for reuse across runtime packages.
  - Acceptance criteria:
    - IC2Constants exposes MOD_ID, LOGGER, and helper methods.
    - IndustrialCodex leverages IC2Constants instead of hardcoded strings.

- [ ] **T032** – Bootstrap DeferredRegister infrastructure (_code_) 
  - Targets: src/main/java/ic2/core/registries/RegistryBootstrap.java, src/main/java/ic2/IndustrialCodex.java
  - Description: Create RegistryBootstrap with DeferredRegisters for blocks, items, block entities, menus, fluids, entity types, recipe types/serializers, sounds, and data components; hook into mod bus.
  - Acceptance criteria:
    - RegistryBootstrap registers all DeferredRegisters to mod event bus.
    - All registry accessors exposed via static methods for content packages.

- [ ] **T033** – Add creative mode tab registry (_code_) 
  - Targets: src/main/java/ic2/core/registries/IC2CreativeTabs.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Define IC2 creative mode tabs leveraging DeferredRegister and supply icon supplier placeholders.
  - Acceptance criteria:
    - Creative mode tab registered via DeferredRegister of CreativeModeTab.
    - Icon supplier references future item safely via Supplier.

- [ ] **T034** – Stub block registry with casing blocks (_code_) 
  - Targets: src/main/java/ic2/content/block/IC2Blocks.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Create IC2Blocks to register machine casing/base blocks needed for future content.
  - Acceptance criteria:
    - IC2Blocks registers foundational casing blocks via RegistryBootstrap.BLOCKS.
    - RegistryBootstrap exposes blocks registrar to other packages.

- [ ] **T035** – Stub block item registration (_code_) 
  - Targets: src/main/java/ic2/content/item/IC2BlockItems.java, src/main/java/ic2/content/block/IC2Blocks.java
  - Description: Ensure casing blocks gain BlockItem entries and prepare helper for later machine registrations.
  - Acceptance criteria:
    - IC2BlockItems registers BlockItems for casing blocks.
    - Block registration defers BlockItem creation to avoid classloading issues.

- [ ] **T036** – Stub standalone item registry (_code_) 
  - Targets: src/main/java/ic2/content/item/IC2Items.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Introduce IC2Items with representative components (circuits, plates) as placeholders for future expansion.
  - Acceptance criteria:
    - IC2Items registers baseline component items via DeferredRegister.
    - RegistryBootstrap exposes ITEMS registrar and ensures creative tab population hook exists.

- [ ] **T037** – Introduce block entity type registry skeleton (_code_) 
  - Targets: src/main/java/ic2/content/blockentity/IC2BlockEntities.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Add IC2BlockEntities with placeholder entries and helper factory methods for machine registration.
  - Acceptance criteria:
    - IC2BlockEntities defines DeferredRegister-backed RegistryObject holders.
    - Utility builder supports registering block entities with block suppliers.

- [ ] **T038** – Introduce menu type registry skeleton (_code_) 
  - Targets: src/main/java/ic2/content/menu/IC2MenuTypes.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Create IC2MenuTypes for machine UI menus using DeferredRegister and placeholder factories.
  - Acceptance criteria:
    - Menu types registered using MenuType constructors appropriate for 1.20.1.
    - Factory helpers prepared for future GUI wiring.

- [ ] **T039** – Introduce fluid registry skeleton (_code_) 
  - Targets: src/main/java/ic2/content/fluid/IC2Fluids.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Add IC2Fluids for fluid types (steam, coolant) with fluid properties placeholders.
  - Acceptance criteria:
    - FluidType and FlowingFluid DeferredRegisters established.
    - Placeholder registry objects declared for key IC2 fluids.

- [ ] **T040** – Introduce entity type registry skeleton (_code_) 
  - Targets: src/main/java/ic2/content/entity/IC2EntityTypes.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Create IC2EntityTypes with placeholders for utility entities (dynamite, itnt, boats).
  - Acceptance criteria:
    - Entity types registered with correct SpawnPlacements and factory suppliers.
    - Future attribute hooks documented via TODOs without deprecated API.

- [ ] **T041** – Introduce recipe type registry (_code_) 
  - Targets: src/main/java/ic2/content/recipe/IC2RecipeTypes.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Define IC2RecipeTypes encapsulating machine recipe types and helper methods for registration.
  - Acceptance criteria:
    - RecipeType holders registered via DeferredRegister.
    - Helper method available for data-driven recipe registration.

- [ ] **T042** – Introduce recipe serializer registry (_code_) 
  - Targets: src/main/java/ic2/content/recipe/IC2RecipeSerializers.java, src/main/java/ic2/content/recipe/IC2RecipeTypes.java
  - Description: Add IC2RecipeSerializers with placeholder serializers and builder utilities.
  - Acceptance criteria:
    - Serializer DeferredRegister populated with base serializer stubs.
    - Serializers reference appropriate recipe type constants.

- [ ] **T043** – Introduce sound event registry (_code_) 
  - Targets: src/main/java/ic2/content/sound/IC2SoundEvents.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Create IC2SoundEvents for machine and tool sounds using DeferredRegister.
  - Acceptance criteria:
    - Sound events registered with namespaced ResourceLocations.
    - Placeholder RegistryObjects declared for major sound categories.

- [ ] **T044** – Introduce data component registry (_code_) 
  - Targets: src/main/java/ic2/content/data/IC2DataComponents.java, src/main/java/ic2/core/registries/RegistryBootstrap.java
  - Description: Register custom DataComponentType entries for IC2 item/block attachments (energy, coolant).
  - Acceptance criteria:
    - DataComponent DeferredRegister initialized and registered.
    - Components declared with codecs/sync codecs ready for use.


## Stage S4 – Events & Lifecycle

- [ ] **T050** – Establish common lifecycle handler (_code_) 
  - Targets: src/main/java/ic2/core/events/CommonLifecycleHandler.java, src/main/java/ic2/IndustrialCodex.java
  - Description: Create CommonLifecycleHandler subscribing to FMLCommonSetupEvent and enqueueing work for registries and network bootstrap.
  - Acceptance criteria:
    - CommonLifecycleHandler listens to mod bus events with proper lambda usage.
    - IndustrialCodex registers handler without deprecated setup hooks.

- [ ] **T051** – Implement module loader bridging (_code_) 
  - Targets: src/main/java/ic2/core/events/ModuleLoader.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Add ModuleLoader to discover @IC2Plugin modules, call IModule lifecycle methods, and wire into event bus.
  - Acceptance criteria:
    - ModuleLoader scans ModList for IC2Plugin annotations and respects Dist gating.
    - Lifecycle handler invokes module load phases at appropriate times.

- [ ] **T052** – Update IC2Classic helper lifecycle (_code_) 
  - Targets: src/main/java/ic2/api/core/IC2Classic.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Connect IC2Classic.setHelper to ModuleLoader results and ensure duplicate set prevention remains.
  - Acceptance criteria:
    - IC2Classic helper is assigned during common setup without violating safeguards.
    - Helper reset is prevented and error messaging preserved.

- [ ] **T053** – Port gameplay event subscriptions (_code_) 
  - Targets: src/main/java/ic2/core/events/GameplayEvents.java, src/main/java/ic2/IndustrialCodex.java
  - Description: Create GameplayEvents class attaching to MinecraftForge event bus for tick/world interactions using modern events.
  - Acceptance criteria:
    - GameplayEvents registers to Forge EVENT_BUS with non-deprecated annotations.
    - Event handlers stubbed for world tick, chunk load, and block break logic.

- [ ] **T054** – Add server lifecycle hooks (_code_) 
  - Targets: src/main/java/ic2/core/events/ServerLifecycleHandler.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Handle server starting/stopping events for save data and energy net management.
  - Acceptance criteria:
    - ServerLifecycleHandler subscribes via EVENT_BUS or Dist-safe registration.
    - Energy/tick managers receive start/stop callbacks.

- [ ] **T055** – Create client lifecycle entrypoint (_code_) 
  - Targets: src/main/java/ic2/client/ClientLifecycle.java, src/main/java/ic2/IndustrialCodex.java
  - Description: Add ClientLifecycle with Dist.CLIENT subscriber to prepare client setup tasks.
  - Acceptance criteria:
    - ClientLifecycle annotated with @Mod.EventBusSubscriber(value = Dist.CLIENT).
    - Registers client setup listener hooking into event bus safely.

- [ ] **T056** – Port color handler registration (_code_) 
  - Targets: src/main/java/ic2/client/render/ColorHandlerRegistrar.java, src/main/java/ic2/client/ClientLifecycle.java
  - Description: Implement ColorHandlerRegistrar to register block/item colors during ColorHandlerEvent.
  - Acceptance criteria:
    - Color handlers registered using modern API without deprecated methods.
    - ClientLifecycle forwards ColorHandlerEvent to registrar.

- [ ] **T057** – Port particle factory registration (_code_) 
  - Targets: src/main/java/ic2/client/particle/ParticleFactoryRegistrar.java, src/main/java/ic2/client/ClientLifecycle.java
  - Description: Register particle factories via RegisterParticleProvidersEvent with Dist gating.
  - Acceptance criteria:
    - Particle factories registered during RegisterParticleProvidersEvent.
    - ClientLifecycle adds listener only on client dist.

- [ ] **T058** – Port entity renderer registration (_code_) 
  - Targets: src/main/java/ic2/client/render/EntityRendererRegistrar.java, src/main/java/ic2/client/ClientLifecycle.java
  - Description: Register entity renderers during EntityRenderersEvent.RegisterRenderers.
  - Acceptance criteria:
    - EntityRendererRegistrar registers renderers for IC2 entities.
    - ClientLifecycle wires event subscriber without mixing server-only code.

- [ ] **T059** – Port client input hooks (_code_) 
  - Targets: src/main/java/ic2/client/input/KeyBindingHandler.java, src/main/java/ic2/client/ClientLifecycle.java
  - Description: Register key bindings and input event handlers using RegisterKeyMappingsEvent and ClientTickEvent.
  - Acceptance criteria:
    - Key bindings registered with proper categories and translations.
    - Input events handle toggles without referencing deprecated classes.


## Stage S5 – Networking

- [ ] **T060** – Introduce IC2Network channel (_code_) 
  - Targets: src/main/java/ic2/network/IC2Network.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Create IC2Network with SimpleChannel, PROTOCOL_VERSION, and registration entry point.
  - Acceptance criteria:
    - SimpleChannel initialized with explicit protocol version and version check.
    - CommonLifecycleHandler triggers packet registration during common setup.

- [ ] **T061** – Implement NetworkManager bridge (_code_) 
  - Targets: src/main/java/ic2/network/NetworkManagerImpl.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Add NetworkManagerImpl implementing INetworkManager and routing to IC2Network packets.
  - Acceptance criteria:
    - NetworkManagerImpl covers INetworkManager methods with stubbed packet dispatch.
    - CommonLifecycleHandler exposes NetworkManagerImpl via API helper.

- [ ] **T062** – Port tile field sync packet (_code_) 
  - Targets: src/main/java/ic2/network/packet/TileFieldSyncPacket.java, src/main/java/ic2/network/IC2Network.java
  - Description: Implement TileFieldSyncPacket with codec, handler, and registration in IC2Network.
  - Acceptance criteria:
    - Packet encodes/decodes target BlockPos and field identifiers using FriendlyByteBuf.
    - Handler schedules client thread updates safely.

- [ ] **T063** – Port tile event packet (_code_) 
  - Targets: src/main/java/ic2/network/packet/TileEventPacket.java, src/main/java/ic2/network/IC2Network.java
  - Description: Implement TileEventPacket for key/value events with server->client/client->server routing.
  - Acceptance criteria:
    - Packet carries BlockPos, key, value, and PacketRange metadata.
    - IC2Network registers packet with correct direction(s).

- [ ] **T064** – Port tile data buffer packet (_code_) 
  - Targets: src/main/java/ic2/network/packet/TileDataBufferPacket.java, src/main/java/ic2/network/IC2Network.java
  - Description: Implement TileDataBufferPacket to sync INetworkDataBuffer payloads.
  - Acceptance criteria:
    - Packet serializes ResourceLocation + buffer payload via INetworkDataBuffer hooks.
    - Handler ensures buffer creation via registered suppliers.

- [ ] **T065** – Port item event packet (_code_) 
  - Targets: src/main/java/ic2/network/packet/ItemEventPacket.java, src/main/java/ic2/network/IC2Network.java
  - Description: Implement ItemEventPacket for player-held items.
  - Acceptance criteria:
    - Packet syncs player ID/item slot with key/value pairs.
    - IC2Network registers server and client handlers appropriately.

- [ ] **T066** – Port item data buffer packet (_code_) 
  - Targets: src/main/java/ic2/network/packet/ItemDataBufferPacket.java, src/main/java/ic2/network/IC2Network.java
  - Description: Implement ItemDataBufferPacket for INetworkDataBuffer on items.
  - Acceptance criteria:
    - Packet encodes stack slot/index plus data buffer ID.
    - Handler guards against empty stacks and schedules updates.

- [ ] **T067** – Implement GUI initial sync packet (_code_) 
  - Targets: src/main/java/ic2/network/packet/GuiInitialDataPacket.java, src/main/java/ic2/network/IC2Network.java
  - Description: Add GuiInitialDataPacket to push CompoundTag snapshots to client screens.
  - Acceptance criteria:
    - Packet transfers CompoundTag and BlockPos/ItemStack context.
    - Client handler applies data to screen/controller safely.

- [ ] **T068** – Implement tracking control packets (_code_) 
  - Targets: src/main/java/ic2/network/packet/TrackingControlPacket.java, src/main/java/ic2/network/IC2Network.java
  - Description: Add StartGuiTrackingPacket/StopGuiTrackingPacket to control auto sync lifetimes.
  - Acceptance criteria:
    - Packet toggles tracking state for players using dimension-safe identifiers.
    - Network registers both directions with appropriate consumers.

- [ ] **T069** – Finalize INetworkManager wiring (_code_) 
  - Targets: src/main/java/ic2/api/network/INetworkManager.java, src/main/java/ic2/network/NetworkManagerImpl.java
  - Description: Update IC2BlockEntities/menus to request sync via NetworkManagerImpl and ensure API helper exposes side-specific managers.
  - Acceptance criteria:
    - INetworkManager gains default helper/static accessor to reach runtime implementation without breaking addons.
    - NetworkManagerImpl provides client/server delegates respecting Dist.


## Stage S6 – Capabilities & Data

- [ ] **T070** – Bootstrap capability attachment events (_code_) 
  - Targets: src/main/java/ic2/core/capabilities/CapabilityBootstrap.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Create CapabilityBootstrap to register capability providers on blocks, items, and entities via AttachCapabilitiesEvent.
  - Acceptance criteria:
    - CapabilityBootstrap subscribes to relevant AttachCapabilitiesEvent variants.
    - CommonLifecycleHandler registers bootstrap during setup.

- [ ] **T071** – Implement tube capability provider (_code_) 
  - Targets: src/main/java/ic2/core/capabilities/TubeCapabilityProvider.java, src/main/java/ic2/core/capabilities/CapabilityBootstrap.java
  - Description: Provide TubeCapabilityProvider exposing ITube capability for tube block entities.
  - Acceptance criteria:
    - Provider attaches capability with stable ResourceLocation.
    - Invalidation handled via LazyOptional.

- [ ] **T072** – Implement notifiable machine capability provider (_code_) 
  - Targets: src/main/java/ic2/core/capabilities/NotifiableMachineCapabilityProvider.java, src/main/java/ic2/core/capabilities/CapabilityBootstrap.java
  - Description: Expose INotifiableMachine capability for machines needing network updates.
  - Acceptance criteria:
    - Provider wraps block entities implementing marker interface.
    - Capability correctly invalidated on block entity removal.

- [ ] **T073** – Implement armor module capability provider (_code_) 
  - Targets: src/main/java/ic2/core/capabilities/ArmorModuleCapabilityProvider.java, src/main/java/ic2/core/capabilities/CapabilityBootstrap.java
  - Description: Attach armor capability to powered armor pieces with appropriate serialization.
  - Acceptance criteria:
    - ItemStack capabilities attached via AttachCapabilitiesEvent<ItemStack>.
    - Provider serializes state via INBTSerializable.

- [ ] **T074** – Create capability sync helper (_code_) 
  - Targets: src/main/java/ic2/core/capabilities/CapabilitySyncUtil.java, src/main/java/ic2/network/NetworkManagerImpl.java
  - Description: Add CapabilitySyncUtil for sending capability state updates via NetworkManagerImpl.
  - Acceptance criteria:
    - Utility exposes methods to queue sync packets for players around block entities.
    - NetworkManagerImpl delegates to helper for NBT conversions.

- [ ] **T075** – Integrate capability bootstrap with block entities (_code_) 
  - Targets: src/main/java/ic2/content/blockentity/machine/BaseMachineBlockEntity.java, src/main/java/ic2/core/capabilities/CapabilityBootstrap.java
  - Description: Update base machine/generator block entities to expose capabilities using new providers.
  - Acceptance criteria:
    - Base machine block entity registers capability providers during initialization.
    - CapabilityBootstrap identifies machine types requiring attachments.

- [ ] **T076** – Attach armor capabilities on equip (_code_) 
  - Targets: src/main/java/ic2/core/capabilities/ArmorModuleCapabilityProvider.java, src/main/java/ic2/core/events/GameplayEvents.java
  - Description: Ensure armor capability provider responds to LivingEquipmentChangeEvent for initialization refresh.
  - Acceptance criteria:
    - Armor capability refreshed when armor equipped/unequipped.
    - Event handler avoids server<->client desync.

- [ ] **T077** – Persist capability data to saved data (_code_) 
  - Targets: src/main/java/ic2/core/capabilities/CapabilitySavedData.java, src/main/java/ic2/core/events/ServerLifecycleHandler.java
  - Description: Introduce SavedData implementation storing global capability state (e.g., energy net, crop data).
  - Acceptance criteria:
    - SavedData registered via ServerLifecycleHandler on server start.
    - Capability state saved and loaded without NPE risk.


## Stage S7 – Configs

- [ ] **T080** – Introduce common config spec (_code_) 
  - Targets: src/main/java/ic2/config/IC2CommonConfig.java, src/main/java/ic2/IndustrialCodex.java
  - Description: Create IC2CommonConfig with ForgeConfigSpec and register via ModLoadingContext.
  - Acceptance criteria:
    - COMMON config spec defines core gameplay toggles and machine balance values.
    - Registered during mod construction with correct file name.

- [ ] **T081** – Introduce client config spec (_code_) 
  - Targets: src/main/java/ic2/config/IC2ClientConfig.java, src/main/java/ic2/client/ClientLifecycle.java
  - Description: Add IC2ClientConfig for rendering/UI toggles and register safely on client dist.
  - Acceptance criteria:
    - Client config registered only on Dist.CLIENT.
    - Config values exposed via safe accessors for rendering code.

- [ ] **T082** – Introduce server config spec (_code_) 
  - Targets: src/main/java/ic2/config/IC2ServerConfig.java, src/main/java/ic2/IndustrialCodex.java
  - Description: Add IC2ServerConfig for server-only balancing and register during common setup.
  - Acceptance criteria:
    - Server config registered and loaded with COMMON as needed.
    - Hot-reload safe listeners ensure values propagate to runtime managers.

- [ ] **T083** – Wire configs into API helper (_code_) 
  - Targets: src/main/java/ic2/core/APIHelperImpl.java, src/main/java/ic2/config/IC2CommonConfig.java
  - Description: Expose config access through APIHelperImpl to maintain addon compatibility.
  - Acceptance criteria:
    - API helper provides getters for config specs/values.
    - Common config exposes static instance used by helper without NPE.

- [ ] **T084** – Handle config reload events (_code_) 
  - Targets: src/main/java/ic2/core/events/CommonLifecycleHandler.java, src/main/java/ic2/config/IC2CommonConfig.java
  - Description: Listen for ModConfigEvent and propagate changes to relevant managers.
  - Acceptance criteria:
    - ModConfigEvent loading/reloading handled without memory leaks.
    - Managers respond to updated values promptly.


## Stage S8 – Datagen & Assets

- [ ] **T090** – Create datagen entrypoint (_code_) 
  - Targets: src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Add IC2DataGenerators registering provider scaffolding for runData.
  - Acceptance criteria:
    - Main datagen class registers to GatherDataEvent via Dist safe listener.
    - Supports server and client data providers.

- [ ] **T091** – Add blockstate/model provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2BlockStateProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Implement blockstate+model provider generating casing and machine states.
  - Acceptance criteria:
    - Blockstate provider outputs JSON for casing blocks.
    - Data generator registers provider only on server data run.

- [ ] **T092** – Add item model provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2ItemModelProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate models for base items and block items.
  - Acceptance criteria:
    - Item models generated for components and tools.
    - Provider respects existing manual overrides when present.

- [ ] **T093** – Add loot table provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2BlockLootProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate block loot tables for casings/machines with correct drops.
  - Acceptance criteria:
    - Loot tables handle silk touch/fortune rules where required.
    - Provider extends BlockLootSubProvider with correct parameter sets.

- [ ] **T094** – Add recipe provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2RecipeProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate machine, crafting, and processing recipes from registries.
  - Acceptance criteria:
    - Recipe provider covers crafting + machine recipes using builder helpers.
    - runData produces valid recipes without errors.

- [ ] **T095** – Add block tags provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2BlockTagsProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate block tags for ores, machine harvest requirements, etc.
  - Acceptance criteria:
    - Block tags provider populates forge tag conventions.
    - Existing resources merged without duplication.

- [ ] **T096** – Add item tags provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2ItemTagsProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate item tags for circuits, plates, cables, and upgrades.
  - Acceptance criteria:
    - Item tags provider syncs with block tags provider where needed.
    - Tags include forge:ingots/* and ic2 categories.

- [ ] **T097** – Add fluid tags provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2FluidTagsProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate fluid tags for steam, coolant, and gases.
  - Acceptance criteria:
    - Fluid tags provider registers forge fluid tags without duplicates.
    - Provider only runs on server data set.

- [ ] **T098** – Add language provider (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2LanguageProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate base en_us lang file for new registry keys while preserving manual translations.
  - Acceptance criteria:
    - Lang provider seeds en_us keys for all registered content.
    - Manual lang files preserved for additional locales.

- [ ] **T099** – Add worldgen data providers (_code_) 
  - Targets: src/main/java/ic2/data/provider/IC2WorldGenProvider.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Generate configured/placed features for ores and rubber trees.
  - Acceptance criteria:
    - Worldgen provider registers configured + placed features for IC2 resources.
    - runData outputs JSON under data/ic2/worldgen without errors.


## Stage S9 – Gameplay Parity & Fixes

- [ ] **T100** – Implement APIHelper runtime bridge (_code_) 
  - Targets: src/main/java/ic2/core/APIHelperImpl.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Create APIHelperImpl wiring fluid container lookup, tick helper, and network manager exposure.
  - Acceptance criteria:
    - APIHelperImpl fulfills APIHelper contract without NPEs.
    - CommonLifecycleHandler assigns helper to IC2Classic during setup.

- [ ] **T101** – Provide tick scheduler implementation (_code_) 
  - Targets: src/main/java/ic2/tick/TickSchedulerImpl.java, src/main/java/ic2/core/APIHelperImpl.java
  - Description: Implement TickSchedulerImpl backing APIHelper.getTickHelper with server-safe scheduling.
  - Acceptance criteria:
    - Tick scheduler queues tasks on server thread respecting level separation.
    - API helper returns singleton instance and clears on server shutdown.

- [ ] **T102** – Introduce base machine block/entity classes (_code_) 
  - Targets: src/main/java/ic2/content/block/machine/BaseMachineBlock.java, src/main/java/ic2/content/blockentity/machine/BaseMachineBlockEntity.java
  - Description: Add reusable BaseMachineBlock and BaseMachineBlockEntity handling energy, inventory, and menu hooks.
  - Acceptance criteria:
    - Base machine classes implement use-with-menu, ticker, and capability exposure without deprecated ITickable.
    - Inventory and energy storage use modern Forge capabilities.

- [ ] **T103** – Register furnace-tier machines (_code_) 
  - Targets: src/main/java/ic2/content/block/IC2Blocks.java, src/main/java/ic2/content/blockentity/IC2BlockEntities.java
  - Description: Add Macerator, Compressor, Extractor blocks/items/block entities referencing base machine classes.
  - Acceptance criteria:
    - Registry objects for core machines exist and tie to block entity constructors.
    - Placeholder logic ensures machines appear in creative tab and datagen lists.

- [ ] **T104** – Introduce generator base classes (_code_) 
  - Targets: src/main/java/ic2/content/block/generator/BaseGeneratorBlock.java, src/main/java/ic2/content/blockentity/generator/BaseGeneratorBlockEntity.java
  - Description: Create BaseGeneratorBlock and BaseGeneratorBlockEntity handling fuel/energy output.
  - Acceptance criteria:
    - Generator base handles energy production tick using capabilities.
    - Includes hooks for fuel burn time and fluid inputs.

- [ ] **T105** – Register generator family blocks (_code_) 
  - Targets: src/main/java/ic2/content/block/IC2Blocks.java, src/main/java/ic2/content/blockentity/IC2BlockEntities.java
  - Description: Register generator blocks (Coal, Geothermal, Solar, Water, Wind) and associated block entities.
  - Acceptance criteria:
    - Generator registry objects defined with appropriate properties and block entity types.
    - Creative tab + datagen placeholders updated accordingly.

- [ ] **T106** – Implement electric tool base (_code_) 
  - Targets: src/main/java/ic2/content/item/tool/ElectricToolItem.java, src/main/java/ic2/content/item/IC2Items.java
  - Description: Add ElectricToolItem base class and migrate drill/chainsaw registration to new system.
  - Acceptance criteria:
    - Electric tools use Forge item capabilities for energy and interact with IC2DataComponents.
    - IC2Items registers drills/chainsaw referencing new class.

- [ ] **T107** – Implement armor module items (_code_) 
  - Targets: src/main/java/ic2/content/item/armor/ArmorModuleItem.java, src/main/java/ic2/content/item/IC2Items.java
  - Description: Create ArmorModuleItem handling module capability and energy, register core modules.
  - Acceptance criteria:
    - Armor modules expose armor capability provider and respect config toggles.
    - Items added to creative tab with proper translation keys.

- [ ] **T108** – Implement crop registry runtime (_code_) 
  - Targets: src/main/java/ic2/crops/CropRegistryImpl.java, src/main/java/ic2/api/crops/ICropRegistry.java
  - Description: Provide CropRegistryImpl fulfilling ICropRegistry API and register default crops/seeds.
  - Acceptance criteria:
    - CropRegistryImpl registers default crops and updates static INSTANCE/weed references.
    - API static access safe-guarded against null before init.

- [ ] **T109** – Implement reactor base classes (_code_) 
  - Targets: src/main/java/ic2/content/block/reactor/NuclearReactorBlock.java, src/main/java/ic2/content/blockentity/reactor/NuclearReactorBlockEntity.java
  - Description: Add NuclearReactorBlock and NuclearReactorBlockEntity scaffolding plus heat management helpers.
  - Acceptance criteria:
    - Reactor block entity manages inventory, heat, and emits appropriate block events.
    - Block handles interactions and renders correct state properties.

- [ ] **T110** – Implement fluid cell items (_code_) 
  - Targets: src/main/java/ic2/content/item/cell/FluidCellItem.java, src/main/java/ic2/content/item/IC2Items.java
  - Description: Create FluidCellItem supporting fluid capabilities and register standard cells.
  - Acceptance criteria:
    - Fluid cells integrate with Forge fluid capability and handle stack interactions.
    - IC2Items registers empty + filled cell variants as needed.

- [ ] **T111** – Add machine recipe builders (_code_) 
  - Targets: src/main/java/ic2/content/recipe/builder/MachineRecipeBuilder.java, src/main/java/ic2/content/recipe/IC2RecipeSerializers.java
  - Description: Introduce MachineRecipeBuilder utilities and hook serializers to support machine recipes.
  - Acceptance criteria:
    - Builder simplifies creation of processing recipes with conditions.
    - Serializers updated to use builder output ensuring codec compliance.

- [ ] **T112** – Restore scrapbox loot system (_code_) 
  - Targets: src/main/java/ic2/content/loot/IC2LootModifiers.java, src/main/java/ic2/data/IC2DataGenerators.java
  - Description: Implement IC2LootModifiers to handle scrapbox drops and integrate with datagen.
  - Acceptance criteria:
    - Global loot modifier registered for scrapbox functionality.
    - Datagen registers modifier provider producing JSON entries.

- [ ] **T113** – Implement foam & miner mechanics (_code_) 
  - Targets: src/main/java/ic2/content/block/foam/FoamSprayerBlock.java, src/main/java/ic2/content/blockentity/foam/FoamSprayerBlockEntity.java
  - Description: Add FoamSprayerBlock/BlockEntity and MinerBlockEntity scaffolding for world interaction tools.
  - Acceptance criteria:
    - Foam sprayer handles block placement and drying timers via new tick scheduler.
    - Miner entity scaffolding interacts with drill/pipes using new capability system.

- [ ] **T114** – Implement compatibility loader (_code_) 
  - Targets: src/main/java/ic2/core/compat/CompatLoader.java, src/main/java/ic2/core/events/CommonLifecycleHandler.java
  - Description: Add CompatLoader to conditionally initialize integrations and invoke from module loader/common setup.
  - Acceptance criteria:
    - CompatLoader checks ModList for partners and registers hooks safely.
    - CommonLifecycleHandler invokes loader during setup without side effects.


## Stage S10 – Docs & Housekeeping

- [ ] **T120** – Update README for 1.20.1 (_docs_) 
  - Targets: (docs only)
  - Description: Refresh README with new version badges, setup instructions, and migration overview.
  - Acceptance criteria:
    - README reflects Forge 47.x / Minecraft 1.20.1 requirements.
    - Includes quickstart for runClient/runData tasks.

- [ ] **T121** – Add BUILDING guide (_docs_) 
  - Targets: (docs only)
  - Description: Document build prerequisites, Gradle tasks, and IDE import steps in BUILDING.md.
  - Acceptance criteria:
    - BUILDING.md created with reproducible build instructions.
    - References configs, datagen, and testing expectations.

- [ ] **T122** – Add CONTRIBUTING guide (_docs_) 
  - Targets: (docs only)
  - Description: Define contribution guidelines, coding standards, and review cadence.
  - Acceptance criteria:
    - CONTRIBUTING.md created with code style (one public class per file) and testing requirements.
    - Links to PLAN/progress workflow for contributors.

- [ ] **T123** – Add migration notes (_docs_) 
  - Targets: (docs only)
  - Description: Author MIGRATION_NOTES_1_20_1.md summarizing major API changes and addon guidance.
  - Acceptance criteria:
    - Migration notes cover registries, networking, configs, and capabilities changes.
    - Document references updated API entry points for addon authors.

- [ ] **T124** – Add GitHub templates (_docs_) 
  - Targets: (docs only)
  - Description: Provide ISSUE_TEMPLATE/PR_TEMPLATE with instructions referencing migration process.
  - Acceptance criteria:
    - .github directory populated with issue/PR templates reflecting Forge 1.20.1 state.
    - Templates mention testing + datagen expectations.

- [ ] **T125** – Final audit & cleanup (_docs_) 
  - Targets: (docs only)
  - Description: Run final audit ensuring PLAN/progress reflect completion, prune obsolete docs/assets, and prepare release notes.
  - Acceptance criteria:
    - PLAN.md and progress.json marked complete for all tasks.
    - Changelog or release notes updated summarizing migration.
