#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define BAREIO_MESSAGE(context, name) BareioObject* bareio_builtin_ ## context ## _ ## name (BareioObject *self, BareioMessage *message, BareioObject *locals)
#define BAREIO_MESSAGES_RESET_CONTEXT ((ptrdiff_t) -2)
#define BAREIO_MESSAGES_END ((ptrdiff_t) -1)

#include "bio-system.h"
#include "bio-types.h"

BareioObject* bareio_run_in_context(BareioScript *script, BareioObject *context);

BAREIO_MESSAGE(globals, halt) {
	bareio_system_halt();

	return self;
}

BAREIO_MESSAGE(string, put) {
	bareio_system_uart_nputs(self->data_string->len, self->data_string->contents);
	bareio_system_uart_puts("\n");

	return self;
}

BAREIO_MESSAGE(string, putRange) {
	BareioObject *start = bareio_run_in_context(message->arguments->members[0], locals);
	BareioObject *end = bareio_run_in_context(message->arguments->members[1], locals);

	bareio_system_uart_nputs(end->data_integer - start->data_integer, self->data_string->contents + start->data_integer);
	bareio_system_uart_puts("\n");

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

	bareio_system_uart_puts(++pos);
	bareio_system_uart_puts("\n");

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
extern BareioBuiltinLookupFunc _bareio_builtin_globals_lookup;

void bareio_runtime_main() {
	BareioObject globals = {
		.builtin_lookup = _bareio_builtin_globals_lookup,
	};

	bareio_run_in_context(&_builtin_script, &globals);
}
