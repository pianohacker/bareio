#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// This is purely a marker for stage0/extract-builtin-message-tables.py.
#define BAREIO_MESSAGE(context, name)
#define BAREIO_MESSAGES_RESET_CONTEXT ((ptrdiff_t) -2)
#define BAREIO_MESSAGES_END ((ptrdiff_t) -1)
#define PSCI_FAST_CALL (1 << 31)
#define PSCI_SECURE_SERVICE_CALL (4 << 24)
#define PSCI_0_2_FN_SYSTEM_OFF (PSCI_FAST_CALL | PSCI_SECURE_SERVICE_CALL | 8)

typedef struct _BareioObject BareioObject;

typedef struct {
	ptrdiff_t name_offset;
	BareioObject *forced_result;
} BareioMessage;

typedef void (BareioBuiltinMessageFunc)(BareioObject *self, BareioMessage *message);

typedef struct {
	ptrdiff_t len;
	char contents[];
} BareioString;

struct _BareioObject {
	BareioBuiltinMessageFunc *builtin_dispatch;

	union {
		BareioString *data_string;
	};
};

volatile unsigned char* UART_START = (unsigned char*) 0x09000000;

void bareio_uart_puts(const char *s) {
	for (; *s; s++) {
		*UART_START = *s;
	}
}

void bareio_uart_nputs(ptrdiff_t n, const char *s) {
	for (ptrdiff_t i = 0; i < n; i++) {
		*UART_START = s[i];
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

void _bareio_builtin_globals_dispatch(BareioObject *self, BareioMessage *message) {
	BareioBuiltinMessageFunc *message_func;

#   include "builtin-message-tables/globals.c"

	message_func(self, message);
}

BAREIO_MESSAGE("string", "put")
void bareio_builtin_string_put(BareioObject *self, BareioMessage *message) {
	bareio_uart_nputs(self->data_string->len, self->data_string->contents);
	bareio_uart_puts("\n");
}

void _bareio_builtin_string_dispatch(BareioObject *self, BareioMessage *message) {
	BareioBuiltinMessageFunc *message_func;

#   include "builtin-message-tables/string.c"

	message_func(self, message);
}

void bareio_run_in_context(BareioMessage *msgs, BareioObject *context) {
	BareioObject *cur_context = context;

	for (BareioMessage *msg = msgs; msg->name_offset != BAREIO_MESSAGES_END; msg++) {
		if (msg->name_offset == BAREIO_MESSAGES_RESET_CONTEXT) {
			cur_context = context;
			continue;
		}

		if (msg->forced_result) {
			cur_context = msg->forced_result;
		}

		if (msg->name_offset < 0) {
			cur_context->builtin_dispatch(cur_context, msg);
		}
	}
}

extern BareioMessage _builtin_messages;

void bareio_runtime_main() {
	BareioObject globals = {
		.builtin_dispatch = _bareio_builtin_globals_dispatch,
	};

	bareio_run_in_context(&_builtin_messages, &globals);
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
