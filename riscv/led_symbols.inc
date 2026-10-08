/* Default exported symbols: first peripheral is a 35x25 LED Matrix.
 * For another GUI allocation pass RV_LED_SYMBOLS=/path/to/exported.inc.
 * The test build substitutes RAM and never pretends CLI has an I/O device.
 */
#if RENDER_TEST
.equ LED_MATRIX_0_BASE, cube_render_test_framebuffer
#else
.equ LED_MATRIX_0_BASE, 0xf0000000
#endif
.equ LED_MATRIX_0_WIDTH, 35
.equ LED_MATRIX_0_HEIGHT, 25
