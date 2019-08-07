#include <stddef.h>
#include <stdint.h>

#define BAREIO_MESSAGE(context, name)

#define BAREIO_HALT ((ptrdiff_t) -1)

typedef struct {
	ptrdiff_t name_offset;
} BareioMessage;

volatile unsigned char* UART_START = (unsigned char*) 0x09000000;

void bareio_uart_puts(char *s) {
	for (; *s; s++) {
		*UART_START = *s;
	}
}

BAREIO_MESSAGE("globals", "say-hi")
void bareio_globals_say_hi() {
	bareio_uart_puts("BareIO!\n");
}

void _bareio_dispatch_globals(ptrdiff_t operation) {
	void (*message_func)();

#   include "builtin-message-tables/globals.c"

	message_func();
}

void bareio_run(BareioMessage *msgs) {
	for (BareioMessage *msg = msgs; msg->name_offset != BAREIO_HALT; msg++) {
		if (msg->name_offset < 0) {
			_bareio_dispatch_globals(msg->name_offset);
		}
	}
}

extern BareioMessage _binary_build_core_iob_start;

void bareio_runtime_main() {
	bareio_run((BareioMessage *) &_binary_build_core_iob_start);
}

extern const void *__stack_top;

void _start() {
	__asm__(
		"ldr x30, =__stack_top;"
		"mov sp, x30;"
		"bl bareio_runtime_main;"
	);

	while (1) {}
}
