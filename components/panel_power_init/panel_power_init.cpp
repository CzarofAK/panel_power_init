#include "panel_power_init.h"
#include "esphome/core/log.h"
#include "esphome/core/hal.h"

namespace esphome {
namespace panel_power_init {

const char *const PanelPowerInit::TAG = "panel_power_init";

void PanelPowerInit::setup() {
  ESP_LOGCONFIG(TAG, "Waking panel PMIC over I2C before DSI init...");
  this->write_byte(0x95, 0x11);
  this->write_byte(0x95, 0x17);
  this->write_byte(0x96, 0x00);
  delay(100);  // NOLINT
  this->write_byte(0x96, 0xFF);
  delay(300);  // NOLINT
}

void PanelPowerInit::dump_config() { ESP_LOGCONFIG(TAG, "Panel Power Init (PMIC wake)"); }

}  // namespace panel_power_init
}  // namespace esphome
