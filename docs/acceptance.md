# Acceptance Gates

## Gate 0 - Ready to create the project

- [x] Requirements, system architecture and pin budget documented
- [x] Exact MCU identified as STM32F103C8T6
- [x] Vendor package contains no reusable `.ioc`
- [x] HSE set to 8 MHz from vendor source and accepted as the project input
- [x] H1 and SWD mapping documented; physical cable verification deferred to connection time
- [x] Vendor schematic revisions accepted unless hardware behavior disagrees
- [x] Git repository initialized on `main` and synchronized to the private remote
- [x] Vendor evidence is ignored, protected by repository policy and was not copied into firmware

## Gate A - Environment ready

- [x] CubeMX 6.18.0-RC3 runtime resolved; project remains on the 6.12.1 compatibility database
- [x] Keil UV4 5.38 executable resolved
- [x] STM32CubeProgrammer CLI 2.16.0 resolved
- [x] Ignored project-local environment file created
- [x] STM32CubeF1 1.8.7 and Keil STM32F1xx DFP 2.4.1 pinned
- [x] Installed DFP contains STM32F103C8
- [x] ARM Compiler 5.06u7 selected for the first C5 baseline; AC6.19 retained for later compatibility builds
- [x] Enhanced doctor completed with exit code 0

## Gate B - Minimal target project

- [x] `.ioc` loads and regenerates the MDK-ARM project
- [x] Keil AC5 target rebuilds with zero errors and zero warnings
- [x] output image path is known
- [ ] reset/startup leaves every motor channel inactive
- [x] diagnostic UART configuration is documented
- [x] no hardware behavior is claimed without testing

## Gate C - Flash and boot

- [ ] explicit flash confirmation used
- [ ] programmer connects over SWD
- [ ] image verifies
- [ ] reset completes
- [ ] boot message is observed

## Gate D - Motor bring-up

- [ ] chassis is raised
- [ ] each wheel mapping is physically verified
- [ ] both directions tested at low duty
- [ ] bounded runtime and automatic stop work
- [ ] communication-loss stop works

## Gate E - PS2 remote control

- [x] PA8 KEY1 input and boot-time SWD allocation regenerate from CubeMX
- [x] PS2 protocol, mapping and mode policy pass host tests with warnings as errors
- [x] Complete target builds with AC5 at zero errors and zero warnings
- [ ] KEY1 idle and pressed polarity measured on the installed board
- [ ] ST-LINK disconnected before PA13/PA14 are reassigned
- [ ] Receiver reports consecutive valid neutral analog frames
- [ ] Short KEY1 press, dead-man release and receiver disconnect each stop the car
- [ ] Long KEY1 press releases PS2 GPIO and SWD reconnects after probe refresh
- [ ] Stick directions are accepted with the chassis raised and low speed limit
