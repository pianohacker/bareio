CMAKE_MINIMUM_REQUIRED(VERSION 3.14)
PROJECT(BareIO C)

INCLUDE_DIRECTORIES(AFTER ${CMAKE_BINARY_DIR})

SET(BAREIO_SOURCES "main.c")
LIST(TRANSFORM BAREIO_SOURCES PREPEND ${CMAKE_SOURCE_DIR}/src/)

SET(BAREIO_BUILTIN_SOURCES "main.io")
LIST(TRANSFORM BAREIO_BUILTIN_SOURCES PREPEND ${CMAKE_SOURCE_DIR}/core/)

ADD_CUSTOM_COMMAND(OUTPUT ${CMAKE_BINARY_DIR}/core.iob
	DEPENDS ${BAREIO_BUILTIN_SOURCES}
	WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
	COMMAND cat ${BAREIO_BUILTIN_SOURCES}
		| python3 stage0/compiler.py
		> ${CMAKE_BINARY_DIR}/core.iob
)

ADD_CUSTOM_COMMAND(OUTPUT ${CMAKE_BINARY_DIR}/core.o
	DEPENDS ${CMAKE_BINARY_DIR}/core.iob
	WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
	COMMAND ${CMAKE_OBJCOPY}
		-I binary
		-O elf64-littleaarch64
		-B aarch64
		--rename-section .data=.rodata,alloc,load,readonly,data,contents
		core.iob
		core.o
)

ADD_CUSTOM_TARGET(_builtin_message_targets
	COMMAND python3 ${CMAKE_SOURCE_DIR}/stage0/extract-builtin-message-tables.py
		${CMAKE_SOURCE_DIR}/src/method-names.lock
		${CMAKE_BINARY_DIR}/builtin-message-tables
		${BAREIO_SOURCES}
)

ADD_LIBRARY(kernel_c_objects OBJECT ${BAREIO_SOURCES})

ADD_DEPENDENCIES(kernel_c_objects _builtin_message_targets)

ADD_CUSTOM_TARGET(kernel ALL
	DEPENDS kernel_c_objects ${CMAKE_BINARY_DIR}/core.o
	COMMAND ${CMAKE_LINKER}
		--no-undefined
		$(CMAKE_BINARY_DIR)/core.o
		$<TARGET_OBJECTS:kernel_c_objects>
		-Map $(CMAKE_BINARY_DIR)/kernel.map
		-o $(CMAKE_BINARY_DIR)/kernel.elf
		-T ${CMAKE_SOURCE_DIR}/kernel.ld
)

ADD_CUSTOM_COMMAND(TARGET kernel POST_BUILD
	COMMAND ${CMAKE_OBJDUMP} -d ${CMAKE_BINARY_DIR}/kernel.elf > ${CMAKE_BINARY_DIR}/kernel.list
)

SET(QEMU_COMMAND "qemu-system-aarch64 -d guest_errors,unimp -M virt -cpu cortex-a57 -nographic -serial mon:stdio" CACHE STRING "QEMU command")
STRING(REGEX REPLACE " " ";" QEMU_COMMAND_LIST ${QEMU_COMMAND})

ADD_CUSTOM_TARGET(qemu
	COMMAND ${QEMU_COMMAND_LIST} -kernel ${CMAKE_BINARY_DIR}/kernel.elf -S -s
	DEPENDS kernel
)

ADD_CUSTOM_TARGET(qemu-nogdb
	COMMAND ${QEMU_COMMAND_LIST} -kernel ${CMAKE_BINARY_DIR}/kernel.elf
	DEPENDS kernel
)