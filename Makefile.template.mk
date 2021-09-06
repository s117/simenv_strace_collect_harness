PRISTINE_SYSROOT = {app_pristine_sysroot}

TOP_DIR = $(PWD)
SIMENV_SYSROOT = $(TOP_DIR)/simenv

APP_INIT_CWD = {app_init_cwd}
APP_NAME = {app_name}
APP_CMD = {app_cmd}
APP_MEMSIZE = {app_memsize}

SIM = {sim_cmd}
SIM_FLAGS = {sim_flags}
FESVR_FLAGS = {fesvr_flags}
PK_FLAGS = {pk_flags}

SIM_FLAGS_EXTRA =
FESVR_FLAGS_EXTRA =
PK_FLAGS_EXTRA =
APP_CMD_EXTRA =

.PHONY: envsetup envclean run

envsetup:
	@ echo Setting up a new simenv at $(SIMENV_SYSROOT)
	cp -fr $(PRISTINE_SYSROOT) $(SIMENV_SYSROOT)
	cp -f  $(RISCV)/riscv64-unknown-elf/bin/pk $(TOP_DIR)

envclean:
	@ echo Removing the simenv at $(SIMENV_SYSROOT)
	@ if [ -e $(SIMENV_SYSROOT) ]; then chmod -R u+w $(SIMENV_SYSROOT); fi
	rm -fr $(SIMENV_SYSROOT)
	rm -fv $(TOP_DIR)/pk

run:
	@ echo Starting simulation
	$(SIM) -m$(APP_MEMSIZE) $(SIM_FLAGS) $(SIM_FLAGS_EXTRA) $(FESVR_FLAGS) $(FESVR_FLAGS_EXTRA) +chroot=$(SIMENV_SYSROOT) +target-cwd=$(APP_INIT_CWD) pk $(PK_FLAGS) $(PK_FLAGS_EXTRA) $(APP_CMD) $(APP_CMD_EXTRA) 2>&1 | tee run.log

clean: envclean
	rm -fv $(TOP_DIR)/*.log
	rm -fv $(TOP_DIR)/*.stdout
	rm -fv $(TOP_DIR)/*.stderr
	rm -fv $(TOP_DIR)/*.trace