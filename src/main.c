#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define BAREIO_MESSAGE(context, name) BareioObject* bareio_builtin_ ## context ## _ ## name (BareioObject *self, BareioMessage *message, BareioObject *locals)
#define BAREIO_MESSAGES_RESET_CONTEXT ((ptrdiff_t) -2)
#define BAREIO_MESSAGES_END ((ptrdiff_t) -1)
#define PSCI_FAST_CALL (1 << 31)
#define PSCI_SECURE_SERVICE_CALL (4 << 24)
#define PSCI_0_2_FN_SYSTEM_OFF (PSCI_FAST_CALL | PSCI_SECURE_SERVICE_CALL | 8)

typedef struct _BareioObject BareioObject;
typedef struct _BareioArguments BareioArguments;

typedef struct {
	ptrdiff_t name_offset;
	BareioObject *forced_result;
	BareioArguments *arguments;
} BareioMessage;

typedef BareioObject* (BareioBuiltinMessageFunc)(BareioObject *self, BareioMessage *message, BareioObject *locals);
typedef BareioBuiltinMessageFunc* (BareioBuiltinLookupFunc)(ptrdiff_t name_offset);

typedef struct {
	void *dummy;
	BareioMessage messages[];
} BareioScript;

typedef struct {
	ptrdiff_t len;
	char contents[];
} BareioString;

struct _BareioObject {
	BareioBuiltinLookupFunc *builtin_lookup;

	union {
		BareioString *data_string;
		int64_t data_integer;
	};
};

struct _BareioArguments {
	ptrdiff_t len;
	BareioScript *members[];
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

BareioObject* bareio_run_in_context(BareioScript *script, BareioObject *context);

void bareio_system_arm_hvc(uint32_t function_id) {
	__asm__(
		"mov x0, %0;"
		"hvc 0;"
		:
		: "r" (function_id)
	);
}

BAREIO_MESSAGE(globals, halt) {
	bareio_system_arm_hvc(PSCI_0_2_FN_SYSTEM_OFF);

	return self;
}

BAREIO_MESSAGE(string, put) {
	bareio_uart_nputs(self->data_string->len, self->data_string->contents);
	bareio_uart_puts("\n");

	return self;
}

BAREIO_MESSAGE(string, putRange) {
	BareioObject *start = bareio_run_in_context(message->arguments->members[0], locals);
	BareioObject *end = bareio_run_in_context(message->arguments->members[1], locals);

	bareio_uart_nputs(end->data_integer - start->data_integer, self->data_string->contents + start->data_integer);
	bareio_uart_puts("\n");

	return self;
}

BAREIO_MESSAGE(integer, put) {
	int64_t i = self->data_integer;
	bool negative = i < 0;

	char buffer[22];
	char *pos = buffer + 21;
	*pos-- = '\0';

	do {
		signed char digit = i % 10;
		*pos-- = '0' + (digit < 0 ? -digit : digit);
		i /= 10;
	} while (i);

	if (negative) {
		*pos-- = '-';
	}

	bareio_uart_puts(++pos);
	bareio_uart_puts("\n");

	return self;
}

BareioObject* bareio_run_in_context(BareioScript *script, BareioObject *context) {
	BareioObject *cur_context = context;
	BareioObject *return_value = context;

	for (BareioMessage *msg = script->messages; msg->name_offset != BAREIO_MESSAGES_END; msg++) {
		if (msg->name_offset == BAREIO_MESSAGES_RESET_CONTEXT) {
			cur_context = context;
			continue;
		}

		if (msg->forced_result) {
			cur_context = return_value = msg->forced_result;
		}

		if (msg->name_offset < 0) {
			cur_context = return_value = (cur_context->builtin_lookup(msg->name_offset))(cur_context, msg, context);
		}
	}

	return return_value;
}

extern BareioScript _builtin_script;

#include "builtin-message-tables.c"

void bareio_runtime_main() {
	BareioObject globals = {
		.builtin_lookup = _bareio_builtin_globals_lookup,
	};

	bareio_run_in_context(&_builtin_script, &globals);
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
