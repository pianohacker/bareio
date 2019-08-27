#ifndef __BIO_TYPES_H__
#define __BIO_TYPES_H__

#include <stddef.h>
#include <stdint.h>

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

#endif
