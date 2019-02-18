.PHONY: all
.PHONY: path_check
.PHONY: runtime
.PHONY: documentation
.PHONY: kernel
.PHONY: test
.PHONY: clean
.PHONY: clean-kernel
.PHONY: distclean

SHELL:=/bin/bash

ISP_PREFIX ?= /opt/isp/

SDK_VERSION:=0.0.0

PROJECTS := riscv-gnu-toolchain
PROJECTS += policy-tool
PROJECTS += policy-engine
PROJECTS += FreeRTOS
PROJECTS += renode-plugins
PROJECTS += renode
PROJECTS += freedom-e-sdk
PROJECTS += riscv-newlib
PROJECTS += llvm-riscv
PROJECTS += qemu

CLEAN_PROJECTS := $(patsubst %,clean-%,$(PROJECTS))

.PHONY: $(PROJECTS)
.PHONY: $(CLEAN_PROJECTS)

all: path_check runtime
	$(MAKE) $(PROJECTS)

policy-engine: policy-tool
renode-plugins: renode
llvm-riscv: riscv-gnu-toolchain
qemu: policy-engine
riscv-newlib: llvm-riscv

path_check:
	(grep -q $(ISP_PREFIX)/bin <<< $(PATH)) || (echo "Need to add $(ISP_PREFIX)/bin to your PATH" && false)

$(PROJECTS): $(ISP_PREFIX)
	$(MAKE) -f Makefile.isp -C ../$@
	$(MAKE) -f Makefile.isp -C ../$@ install

$(ISP_PREFIX):
	sudo mkdir -p $(ISP_PREFIX)
	sudo chown $(USER) $(ISP_PREFIX)

$(CLEAN_PROJECTS):
	$(MAKE) -f Makefile.isp -C ../$(@:clean-%=%) clean

runtime:
	$(MAKE) -C runtime install

documentation:
	$(MAKE) -C documentation

test-qemu:
	$(MAKE) -C ../policies/policy_tests qemu

test-renode:
	$(MAKE) -C ../policies/policy_tests renode

clean-test:
	$(MAKE) -C ../policies/policy_tests clean

clean: $(CLEAN_PROJECTS) clean-test

distclean: clean
	sudo rm -rf $(ISP_PREFIX)
