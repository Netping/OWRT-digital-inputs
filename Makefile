SECTION="NetPing modules"
CATEGORY="Base"
TITLE="EPIC OWRT-Digital-inputs"

PKG_NAME="OWRT-Digital-inputs"
PKG_VERSION="Epic.V0.1"
PKG_RELEASE=1

MODULE_FILES=
MODULE_FILES_DIR=/usr/lib/python3.7/

CONF_FILE=diginsensorconf
CONF_DIR=/etc/config/

.PHONY: all install

all: install

install:
	cp $(CONF_FILE) $(CONF_DIR)
	for f in $(MODULE_FILES); do cp $${f} $(MODULE_FILES_DIR); done

clean:
	rm -f $(CONF_DIR)$(CONF_FILE)
	for f in $(MODULE_FILES); do rm -f $(MODULE_FILES_DIR)$${f}; done