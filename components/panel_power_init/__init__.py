# =============================================================================
# panel_power_init - I2C wake-up for the 10.1-DSI-TOUCH-A panel's PMIC
# =============================================================================
# Works around esphome/esphome#15564: the JD9365 panel on this Waveshare
# board apparently sits behind a small power-management IC that stays
# asleep after a cold boot until it is woken over I2C. ESPHome's built-in
# WAVESHARE-10.1-DSI-TOUCH-A model does not do this wake-up, so
# display.mipi_dsi's own setup() sends its DCS init sequence straight into
# a panel that never acknowledges it - ESP-IDF's
# mipi_dsi_hal_host_gen_write_dcs_command() then spins forever inside
# mipi_dsi_host_ll_gen_is_cmd_fifo_full(), and the task watchdog kills
# loopTask (CPU1) about 5s later, right after the
# "display.mipi_dsi:024]: Running Setup" log line.
#
# This component performs the wake sequence reported to fix it in
# esphome/esphome#15564 (open as of 2026-09-10, one reporter, "works fine
# in my project" - not yet independently confirmed by another user or an
# ESPHome maintainer). The reporter sources the register values from
# Waveshare's own ESP-IDF LCD driver for this panel, not a guess - a
# meaningfully better provenance than a random forum post, but still not
# this board's own datasheet, and still only one report. It is
# deliberately given a setup_priority just below i2c's own BUS priority
# so it always runs before display.mipi_dsi's setup() - see the .h file's
# own comment on why that ordering is load-bearing here.
#
# ⚠ NOT yet verified against this specific board's own PMIC datasheet -
# no datasheet was available when this was written, and the upstream
# issue itself has no independent confirmation yet either. The register
# addresses/values/delays below are exactly what the upstream report
# used, not derived from first principles. Before flashing this: check
# the relevant I2C bus's own scan log (`i2c: {..., scan: true}`) for
# "Found device at address 0x45" - if it's not there, this isn't the same
# PMIC/address on that board and this fix doesn't apply as-is (a
# different address would need swapping in below). See this repo's
# README for the full write-up and verification status.

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import i2c
from esphome.const import CONF_ID

DEPENDENCIES = ["i2c"]
CODEOWNERS = ["@CzarofAK"]

panel_power_init_ns = cg.esphome_ns.namespace("panel_power_init")
PanelPowerInit = panel_power_init_ns.class_(
    "PanelPowerInit", cg.Component, i2c.I2CDevice
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(PanelPowerInit),
    }
).extend(i2c.i2c_device_schema(0x45))


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await i2c.register_i2c_device(var, config)
