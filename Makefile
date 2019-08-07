# Originally based on bare-metal Makefile for ARM by Alex Chadwick, under the MIT License:
#
# Copyright (c) 2012 Alex Chadwick
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

ARMGNU ?= $(HOME)/c/gcc-linaro-7.1.1-2017.08-x86_64_aarch64-elf/bin/aarch64-elf

BUILD_DIR = build
SOURCE_DIR = src

TARGET = $(BUILD_DIR)/kernel.elf
LIST = $(BUILD_DIR)/kernel.list
MAP = $(BUILD_DIR)/kernel.map
LINKER = kernel.ld

SOURCES = $(wildcard $(SOURCE_DIR)/*.c)
OBJECTS := $(patsubst $(SOURCE_DIR)/%.c,$(BUILD_DIR)/%.o,$(SOURCES))
BUILTINS := $(wildcard $(SOURCE_DIR)/*.add)

TARGET_CPU = cortex-a57
CFLAGS = -nostdlib -mcpu=$(TARGET_CPU) -g -I $(SOURCE_DIR) -I $(BUILD_DIR)

QEMU := qemu-system-aarch64
QEMUFLAGS := -d guest_errors,unimp -M virt -cpu $(TARGET_CPU) -nographic -serial mon:stdio

all: $(TARGET) $(LIST)

rebuild: clean all

$(LIST) : $(BUILD_DIR)/kernel.elf
	$(ARMGNU)-objdump -d $(BUILD_DIR)/kernel.elf > $(LIST)

$(BUILD_DIR)/kernel.elf : $(OBJECTS) $(LINKER)
	$(ARMGNU)-ld --no-undefined $(OBJECTS) -Map $(MAP) -o $(BUILD_DIR)/kernel.elf -T $(LINKER)

$(BUILD_DIR)/%.o: $(SOURCE_DIR)/%.c $(BUILD_DIR)
	$(ARMGNU)-gcc $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/%.S: $(SOURCE_DIR)/%.c $(BUILD_DIR)
	$(ARMGNU)-gcc $(CFLAGS) -S -c $< -o $@

$(BUILD_DIR)/builtins.add: $(BUILTINS)
	cat $(BUILTINS) > $@

# $(BUILD_DIR)/main.o: $(BUILD_DIR)/builtins.add

$(BUILD_DIR):
	mkdir $@

qemu: all
	$(QEMU) $(QEMUFLAGS) -kernel build/kernel.elf -S -s

qemu-nogdb: all
	$(QEMU) $(QEMUFLAGS) -kernel build/kernel.elf

gdb:
	$(ARMGNU)-gdb build/kernel.elf -ex 'target remote localhost:1234' -ex 'set confirm off' -ex 'layout prev'

clean : 
	-rm -rf $(BUILD_DIR)
	-rm -f $(TARGET)
	-rm -f $(LIST)
	-rm -f $(MAP)
