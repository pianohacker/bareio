#include <stddef.h>
#include <stdint.h>

// This is purely a marker for stage0/extract-builtin-message-tables.py.
#define BAREIO_MESSAGE(context, name)
#define BAREIO_MESSAGES_END ((ptrdiff_t) -1)
#define PSCI_FAST_CALL (1 << 31)
#define PSCI_SECURE_SERVICE_CALL (4 << 24)
#define PSCI_0_2_FN_SYSTEM_OFF (PSCI_FAST_CALL | PSCI_SECURE_SERVICE_CALL | 8)

typedef struct {
	ptrdiff_t name_offset;
} BareioMessage;

typedef struct _BareioObject BareioObject;

typedef void (BareioBuiltinMessageFunc)(BareioObject *self, BareioMessage *message);

struct _BareioObject {
	BareioBuiltinMessageFunc *builtin_dispatch;
};

volatile unsigned char* UART_START = (unsigned char*) 0x09000000;

void bareio_uart_puts(char *s) {
	for (; *s; s++) {
		*UART_START = *s;
	}
}

BAREIO_MESSAGE("globals", "say-hi")
void bareio_builtin_globals_say_hi(BareioObject *self, BareioMessage *message) {
	bareio_uart_puts("BareIO!\n");
}

void bareio_system_arm_hvc(uint32_t function_id) {
	__asm__(
		"mov x0, %0;"
		"hvc 0;"
		:
		: "r" (function_id)
	);
}

BAREIO_MESSAGE("globals", "halt")
void bareio_builtin_globals_halt(BareioObject *self, BareioMessage *message) {
	bareio_system_arm_hvc(PSCI_0_2_FN_SYSTEM_OFF);
}

void _bareio_dispatch_globals(BareioObject *self, BareioMessage *message) {
	BareioBuiltinMessageFunc *message_func;

#   include "builtin-message-tables/globals.c"

	message_func(self, message);
}

void bareio_run_in_context(BareioMessage *msgs, BareioObject *context) {
	for (BareioMessage *msg = msgs; msg->name_offset != BAREIO_MESSAGES_END; msg++) {
		if (msg->name_offset < 0) {
			context->builtin_dispatch(context, msg);
		}
	}
}

extern BareioMessage _binary_build_core_iob_start;

void bareio_runtime_main() {
	BareioObject globals = {
		.builtin_dispatch = _bareio_dispatch_globals,
	};

	bareio_run_in_context((BareioMessage *) &_binary_build_core_iob_start, &globals);
}

extern const void *__stack_top;

void _start() {
	__asm__(
		"ldr x30, =__stack_top;"
		"mov sp, x30;"
		"bl bareio_runtime_main;"
		"loop:"
		"wfi;"
		"b loop;"
	);
}
