#include <stddef.h>
#include <stdint.h>

#define PSCI_FAST_CALL (1 << 31)
#define PSCI_SECURE_SERVICE_CALL (4 << 24)
#define PSCI_0_2_FN_SYSTEM_OFF (PSCI_FAST_CALL | PSCI_SECURE_SERVICE_CALL | 8)

volatile uint8_t* UART_START = (unsigned char*) 0x09000000;

void bareio_system_arm_hvc(uint32_t function_id) {
	__asm__(
		"mov x0, %0;"
		"hvc 0;"
		:
		: "r" (function_id)
	);
}

void bareio_system_halt() {
	bareio_system_arm_hvc(PSCI_0_2_FN_SYSTEM_OFF);
}

void bareio_system_uart_puts(const char *s) {
	for (; *s; s++) {
		*UART_START = *s;
	}
}

void bareio_system_uart_nputs(ptrdiff_t n, const char *s) {
	for (ptrdiff_t i = 0; i < n; i++) {
		*UART_START = s[i];
	}
}
