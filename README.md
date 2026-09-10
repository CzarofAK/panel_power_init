# panel_power_init

A small, single-purpose ESPHome component: wakes a panel's I2C-controlled
PMIC over I2C before `display.mipi_dsi` runs its own `setup()`. Written for
the Waveshare **10.1-DSI-TOUCH-A** panel (JD9365, ESP32-P4 boards), as a
workaround for [esphome/esphome#15564](https://github.com/esphome/esphome/issues/15564).

## The problem this works around

On some ESP32-P4 + `WAVESHARE-10.1-DSI-TOUCH-A` boards, boot hangs right
after this log line:

```
[C][display.mipi_dsi:024]: Running Setup
```

...then ESP-IDF's task watchdog kills `loopTask` (CPU1) about 5 seconds
later, with a register dump decoding to:

```
mipi_dsi_host_ll_gen_is_cmd_fifo_full at .../hal/mipi_dsi_host_ll.h:723
 (inlined by) mipi_dsi_hal_host_gen_write_dcs_command at .../mipi_dsi_hal.c:165
```

[esphome/esphome#15564](https://github.com/esphome/esphome/issues/15564)
(open as of 2026-09-10, filed against this exact board/panel, ESPHome
2026.3.3) attributes this to a small PMIC sitting behind the JD9365 panel
that stays asleep after a cold boot until woken over I2C - without that
wake-up, the panel never ACKs the DCS init sequence ESPHome's built-in
`WAVESHARE-10.1-DSI-TOUCH-A` model sends, and
`mipi_dsi_hal_host_gen_write_dcs_command()` spins forever waiting for room
in the command FIFO that will never drain.

The reporter's fix - reproduced here - sends this sequence to I2C address
`0x45` before the display's own `setup()` runs:

| Register | Value | Then |
|---|---|---|
| `0x95` | `0x11` | |
| `0x95` | `0x17` | |
| `0x96` | `0x00` | wait 100ms |
| `0x96` | `0xFF` | wait 300ms |

Sourced (per the reporter) from Waveshare's own ESP-IDF LCD driver, not a
guess - better provenance than a random forum post, but still only **one**
report, not yet confirmed by another user or an ESPHome maintainer.

## Why a component, not `on_boot:`

The hang is *inside* `display.mipi_dsi`'s own `setup()`. ESPHome runs every
component's `setup()` in one pass, highest `setup_priority` first;
`on_boot:` automations only run after every component has already finished
setup. By the time an `on_boot:` trigger could fire, the board has already
watchdog-reset. The only way to run code before the display's `setup()` is
another component with a higher `setup_priority`.

This component uses `setup_priority::BUS - 1.0f` - `i2c`'s own bus
component sits at `setup_priority::BUS` (1000, the highest ESPHome defines
besides `POWER`), and `display.mipi_dsi` inherits `display::Display`'s
default (`setup_priority::PROCESSOR`, 400). Sitting one step below `BUS`
guarantees this component's `setup()` (the wake sequence) runs after the
I2C bus is initialized but before the display's `setup()` - confirmed
directly against ESPHome's own `esphome/core/component.h`, not assumed.

## Usage

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/CzarofAK/panel_power_init
      ref: main
    components: [panel_power_init]

panel_power_init:
  i2c_id: bus_touch   # the i2c: bus the PMIC is actually on
  address: 0x45       # default if omitted
```

See [`examples/example.yaml`](examples/example.yaml) for a fuller snippet
alongside the `i2c:`/`esp_ldo:`/`display:` blocks it depends on.

## Configuration reference

| Key | Type | Default | Meaning |
|---|---|---|---|
| `i2c_id` | id | the only/default `i2c:` bus | which `i2c:` bus the PMIC is on |
| `address` | int | `0x45` | the PMIC's I2C address |

## ⚠ Before you flash this

Check your board's own `i2c:` scan log (`i2c: { ..., scan: true }`) for
`Found device at address 0x45` **before** trusting this applies to your
board. This component's I2C writes go out unconditionally regardless of
whether anything is listening - `write_byte()`'s return value isn't
checked, so a wrong or absent address fails silently rather than erroring.
If `0x45` never shows up on your scan, this isn't the same PMIC/address on
your board, and this component won't fix your crash as-is.

## Verification status

- [esphome/esphome#15564](https://github.com/esphome/esphome/issues/15564)
  is real and open, filed against this exact board/panel/model string,
  register values sourced from Waveshare's own ESP-IDF driver per the
  reporter - not independently confirmed by a second user or an ESPHome
  maintainer as of this writing.
- `i2c::I2CDevice::write_byte(reg, data)` and the `setup_priority`
  ordering this component relies on (`BUS` = 1000, descending priority =
  earlier `setup()`) were both confirmed directly against ESPHome's own
  `esphome/core/i2c/i2c.h` and `esphome/core/component.h` source, not
  assumed.
- **Not yet confirmed on real hardware end-to-end.** First real-world test
  (on an ESP32-P4-WIFI6-POE-ETH + 10.1-DSI-TOUCH-A board, in
  `smartebl_display_esphome`) reproduced the exact crash this component
  targets, but a scan of that board's touch-controller I2C bus - even at
  `logger: level: VERY_VERBOSE` - showed **no** `i2c.idf` scan output at
  all (neither a "Scanning for devices" line nor any "Found device at
  address 0x.." line), which is inconclusive rather than a clean
  "0x45 not present" result: it doesn't confirm the PMIC is there, but it
  also doesn't rule this fix out - something about why the scan itself
  isn't logging anything is still open. Treat this component as untested
  until that's resolved and a build with it applied is flashed and
  confirmed to boot past `display.mipi_dsi`'s `setup()`.
