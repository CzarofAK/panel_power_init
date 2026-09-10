#pragma once
#include "esphome/core/component.h"
#include "esphome/components/i2c/i2c.h"

namespace esphome {
namespace panel_power_init {

// See __init__.py's header comment (and this repo's README) for the full
// "why" - short version: the 10.1-DSI-TOUCH-A panel's PMIC needs this I2C
// wake sequence before display.mipi_dsi starts sending DSI init commands,
// or the panel never acks them and the task watchdog kills loopTask ~5s
// into setup().
class PanelPowerInit : public Component, public i2c::I2CDevice {
 public:
  // MUST run before display.mipi_dsi's own setup() - ESPHome runs every
  // component's setup() in one pass, highest setup_priority first, and
  // the hang happens INSIDE display.mipi_dsi's setup() itself, so there
  // is no on_boot/automation hook late enough to reach - by the time an
  // on_boot trigger could fire, the watchdog has already reset the board.
  // i2c's own bus component uses setup_priority::BUS (1000, the highest
  // priority ESPHome defines besides POWER) so the bus is guaranteed
  // initialized first; display.mipi_dsi inherits display::Display's
  // default (setup_priority::PROCESSOR, 400) - sitting one step below
  // BUS still safely beats it, and every other ordinary component too.
  float get_setup_priority() const override { return setup_priority::BUS - 1.0f; }

  void setup() override;
  void dump_config() override;

 protected:
  static const char *const TAG;
};

}  // namespace panel_power_init
}  // namespace esphome
