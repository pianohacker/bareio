#include <stddef.h>
#include <stdint.h>

extern const void *__stack_top;
volatile unsigned char* UART_START = (unsigned char*) 0x09000000;

#define BAREIO_IS_BUILTIN_MESSAGE ((ptrdiff_t) PTRDIFF_MIN)
#define BAREIO_HALT ((ptrdiff_t) -1)

typedef struct {
	ptrdiff_t name_offset;
} BareioMessage;

void bareio_uart_puts(char *s) {
	for (; *s; s++) {
		*UART_START = *s;
	}
}

void bareio_say_hi() {
	bareio_uart_puts("BareIO!\n");
}

void (*builtin_msgs[])() = {
	bareio_say_hi,
};

void bareio_run(BareioMessage *msgs) {
	for (BareioMessage *msg = msgs; msg->name_offset != BAREIO_HALT; msg++) {
		if (msg->name_offset & BAREIO_IS_BUILTIN_MESSAGE) {
			builtin_msgs[msg->name_offset ^ BAREIO_IS_BUILTIN_MESSAGE]();
		}
	}
}

BareioMessage hardcoded[] = {
	{ BAREIO_IS_BUILTIN_MESSAGE | (0) },
	{ BAREIO_HALT },
};

void bareio_runtime_main() {
	bareio_run(hardcoded);
}

void _start() {
	__asm__(
		"ldr x30, =__stack_top;"
		"mov sp, x30;"
		"bl bareio_runtime_main;"
	);

	while (1) {}
}
