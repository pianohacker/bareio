#ifndef __BIO_SYSTEM_H__
#define __BIO_SYSTEM_H__

#include <stddef.h>
#include <stdint.h>

extern void bareio_system_halt();
void bareio_system_uart_puts(const char *s);
void bareio_system_uart_nputs(ptrdiff_t n, const char *s);

#endif
