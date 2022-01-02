SECTION="NetPing modules"
CATEGORY="Base"
TITLE="EPIC OWRT-Digital-inputs"

PKG_NAME="OWRT-Digital-inputs"
PKG_VERSION="Epic.V0.1"
PKG_RELEASE=7

MODULE_FILES=
MODULE_FILES_DIR=/usr/lib/python3.7/

ETC_FILES=Configname owrt_digital_inputs.py
ETC_FILES_DIR=/etc/netping_digital_inputs/

CONF_FILE=diginsensorconf
CONF_DIR=/etc/config/

.PHONY: all install

all: install

install:
	cp $(CONF_FILE) $(CONF_DIR)
	for f in $(MODULE_FILES); do cp $${f} $(MODULE_FILES_DIR); done
	mkdir $(ETC_FILES_DIR)
	for f in $(ETC_FILES); do cp $${f} $(ETC_FILES_DIR); done
	mkdir $(ETC_FILES_DIR)/commands

clean:
	rm -f $(CONF_DIR)$(CONF_FILE)
	for f in $(MODULE_FILES); do rm -f $(MODULE_FILES_DIR)$${f}; done
	rm -rf $(ETC_FILES_DIR)