/* Originally based on bare-metal linker script for ARM by Alex Chadwick, under the MIT License:
 *
 *
 * Copyright (c) 2012 Alex Chadwick

 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following
 * conditions:

 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.

 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 **/

ENTRY(_start)

SECTIONS {
	/* This is the base loader address for a virtual QEMU ARM machine. */
	. = 0x41000000;

	.init : {
		*(.init)
	}
	
	.text : {
		*(.text)
	}

	. = ALIGN(4096);
	.data : {
		*(.data)
		__data_seg_end = .;
	}

	. = ALIGN(4096);
	.rodata : {
		*(.rodata)
		__rodata_seg_end = .;
	}

	. = ALIGN(4096) + 8M;
	__stack_top = .;
}
