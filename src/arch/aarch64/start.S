.global _start
_start:

ldr x30, =__stack_top;
mov sp, x30;
bl bareio_runtime_main;

loop:
wfi;
b loop;
