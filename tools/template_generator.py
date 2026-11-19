#!/usr/bin/env python3
"""
SeedQR Template Generator

Generates front and back SVG templates for SeedQR backup cards.
- Front: QR code grid with finder patterns, fingerprint field, notes
- Back: Word list for writing seed words

Usage:
    python template_generator.py 21 12
    python template_generator.py 25 24 --title "My Wallet" --color "#ff6600"
"""

import argparse
import io
import math
from dataclasses import dataclass


def get_logo_svg_content():
    """Return the embedded SeedSigner logo SVG inner content."""
    return '''<style type="text/css">
	.st0{fill:#FF7300;}
	.st1{fill:#FFFFFF;}
</style>
<g>
	<path class="st0" d="M569.64,542.84c2.02,3.52,3.02,7.85,3.02,12.98s-1.02,9.66-3.08,13.57c-2.05,3.91-4.74,6.93-8.06,9.06c-6.4,4.19-13.23,6.28-20.5,6.28c-3.71,0-7.22-0.45-10.54-1.36c-3.32-0.91-6.01-2.03-8.06-3.38c-4.19-2.52-7.11-4.97-8.77-7.34l-1.07-1.31c-2.05-2.53-3.07-4.8-3.07-6.81c0-2.02,1.69-4.68,5.09-8c1.97-1.9,4.07-2.84,6.28-2.84s5.29,1.97,9.24,5.92c1.11,1.34,2.69,2.63,4.74,3.85c2.06,1.23,3.95,1.84,5.69,1.84c7.35,0,11.02-3,11.02-9.01c0-1.81-1.01-3.33-3.02-4.56c-2.01-1.22-4.52-2.11-7.53-2.67c-3-0.55-6.24-1.44-9.71-2.66c-3.48-1.23-6.72-2.67-9.72-4.33c-3-1.66-5.51-4.28-7.52-7.88c-2.02-3.59-3.03-7.92-3.03-12.97c0-6.95,2.59-13.02,7.76-18.19c5.18-5.18,12.23-7.76,21.16-7.76c4.74,0,9.06,0.61,12.97,1.83c3.91,1.23,6.62,2.47,8.12,3.74l2.96,2.25c2.45,2.29,3.68,4.22,3.68,5.81c0,1.58-0.95,3.75-2.85,6.51c-2.69,3.95-5.45,5.93-8.29,5.93c-1.66,0-3.72-0.79-6.16-2.37c-0.24-0.16-0.7-0.56-1.37-1.19c-0.67-0.63-1.28-1.14-1.83-1.54c-1.66-1.03-3.78-1.54-6.34-1.54c-2.57,0-4.7,0.61-6.4,1.84c-1.7,1.22-2.55,2.92-2.55,5.09c0,2.18,1.01,3.93,3.02,5.28c2.02,1.34,4.52,2.25,7.53,2.72c3,0.47,6.28,1.21,9.83,2.19c3.56,0.99,6.83,2.2,9.84,3.62C565.12,536.86,567.63,539.33,569.64,542.84z"/>
	<path class="st0" d="M605.67,501.21c0.39,1.34,0.59,3.39,0.59,6.16v65.88c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.12,3.08c-1.11,2.14-4.19,3.2-9.25,3.2c-5.53,0-8.76-1.5-9.71-4.5c-0.48-1.27-0.72-3.28-0.72-6.05v-65.88c0-1.81,0.06-3.18,0.18-4.09c0.12-0.9,0.49-1.95,1.13-3.14c1.11-2.13,4.18-3.2,9.24-3.2C601.36,496.82,604.64,498.28,605.67,501.21z"/>
	<path class="st0" d="M695.09,534.62c0.79,1.5,1.19,3.72,1.19,6.64v26.07c0,2.53-1.11,4.94-3.32,7.23c-6.63,6.87-16.59,10.31-29.86,10.31c-11.77,0-22-4.45-30.69-13.33c-8.69-8.89-13.03-19.62-13.03-32.18s4.42-23.05,13.27-31.46c8.85-8.41,19.27-12.62,31.28-12.62c9.32,0,18.13,3.08,26.43,9.24c2.13,1.58,3.19,3.35,3.19,5.28s-0.9,4.17-2.72,6.69c-3.08,4.19-5.89,6.28-8.42,6.28c-1.5,0-3.9-1.08-7.22-3.25c-3.32-2.18-7.27-3.26-11.85-3.26c-6.01,0-11.34,2.11-16,6.33c-4.66,4.23-6.99,9.76-6.99,16.6c0,6.83,2.37,12.64,7.11,17.41c4.74,4.78,10.11,7.17,16.12,7.17c4.34,0,8.25-0.71,11.73-2.13v-12.91h-9.37c-2.44,0-4.18-0.32-5.21-0.96c-1.03-0.62-1.7-1.55-2.01-2.78c-0.32-1.22-0.48-2.88-0.48-4.98c0-2.09,0.18-3.77,0.53-5.03c0.36-1.26,1.01-2.14,1.96-2.61c1.42-0.71,3.32-1.07,5.69-1.07h20.85C691.54,531.46,694.15,532.57,695.09,534.62z"/>
	<path class="st0" d="M784.03,501.44c0.47,1.27,0.71,3.28,0.71,6.05v65.76c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.13,3.08c-1.1,2.14-4.18,3.2-9.24,3.2c-3.08,0-5.21-0.24-6.4-0.71c-1.18-0.47-2.17-1.23-2.96-2.25c-17.77-23.7-29.47-39.18-35.07-46.45v38.98c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.13,3.08c-1.1,2.14-4.18,3.2-9.24,3.2c-4.9,0-7.9-1.06-9.01-3.2c-0.63-1.18-1-2.25-1.12-3.2s-0.18-2.33-0.18-4.15v-66.12c0-3,0.37-5.19,1.13-6.57c0.75-1.38,1.87-2.31,3.37-2.79c1.51-0.47,3.44-0.71,5.81-0.71s4.25,0.22,5.63,0.65c1.38,0.44,2.35,0.93,2.9,1.49c0.32,0.23,1.22,1.26,2.73,3.08c16.66,22.67,27.8,37.64,33.41,44.9v-40.05c0-3,0.38-5.19,1.13-6.57s1.87-2.31,3.38-2.79c1.49-0.47,3.38-0.71,5.63-0.71s4.06,0.2,5.44,0.59c1.39,0.4,2.42,0.88,3.09,1.42C783.22,499.51,783.71,500.34,784.03,501.44z"/>
	<path class="st0" d="M818.33,517.8v11.97h23.46c1.82,0,3.18,0.06,4.09,0.17c0.91,0.12,1.96,0.5,3.14,1.13c2.13,1.1,3.2,4.19,3.2,9.24c0,5.53-1.5,8.77-4.5,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-23.23v11.97h36.5c1.82,0,3.18,0.06,4.09,0.17c0.9,0.12,1.95,0.5,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.47,8.77-4.39,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-46.92c-5.53,0-8.77-1.5-9.72-4.5c-0.47-1.27-0.71-3.28-0.71-6.05v-65.88c0-4.03,0.75-6.77,2.25-8.23c1.5-1.47,4.34-2.2,8.53-2.2h46.69c1.82,0,3.18,0.06,4.09,0.18c0.9,0.12,1.95,0.49,3.14,1.13c2.13,1.1,3.2,4.18,3.2,9.24c0,5.53-1.47,8.77-4.39,9.72c-1.34,0.47-3.4,0.71-6.16,0.71H818.33z"/>
	<path class="st0" d="M946.13,575.15c0,3-2.45,5.53-7.34,7.58c-2.53,1.11-4.56,1.66-6.1,1.66c-1.55,0-2.81-0.37-3.8-1.12s-1.72-1.53-2.19-2.32c-0.79-1.5-3.87-8.65-9.24-21.44l-3.68,0.23h-14.93v13.39c0,1.82-0.05,3.18-0.18,4.09c-0.11,0.91-0.49,1.96-1.12,3.14c-1.11,2.14-4.19,3.2-9.24,3.2c-5.53,0-8.77-1.46-9.72-4.38c-0.47-1.34-0.71-3.4-0.71-6.16v-65.77c0-1.81,0.06-3.18,0.18-4.09c0.11-0.9,0.49-1.95,1.12-3.14c1.11-2.13,4.19-3.2,9.24-3.2h25.6c6.95,0,13.71,2.53,20.26,7.59c3.16,2.45,5.77,5.76,7.82,9.95c2.06,4.19,3.09,8.85,3.09,13.98c0,8.93-2.97,16.28-8.89,22.04c1.74,4.19,4.42,10.39,8.05,18.61C945.54,571.83,946.13,573.88,946.13,575.15z"/>
	<g>
		<path class="st0" d="M136.94,572.78c-2.05-2.53-3.08-4.8-3.08-6.81c0-2.02,1.69-4.68,5.09-8c1.97-1.9,4.07-2.84,6.28-2.84s5.29,1.98,9.24,5.92c1.11,1.34,2.69,2.63,4.74,3.85c2.05,1.23,3.95,1.84,5.69,1.84c7.35,0,11.02-3,11.02-9.01c0-1.82-1.01-3.33-3.02-4.56c-2.01-1.23-4.52-2.12-7.52-2.67c-3-0.55-6.24-1.44-9.72-2.67c-3.48-1.22-6.72-2.66-9.72-4.32c-3-1.66-5.51-4.29-7.52-7.88c-2.01-3.59-3.02-7.92-3.02-12.98c0-6.95,2.59-13.01,7.76-18.19c5.17-5.17,12.23-7.76,21.16-7.76c4.74,0,9.06,0.61,12.97,1.84c3.91,1.23,6.62,2.47,8.12,3.73l2.96,2.25c2.45,2.29,3.67,4.23,3.67,5.81s-0.95,3.75-2.84,6.52c-2.69,3.95-5.45,5.92-8.3,5.92c-1.66,0-3.71-0.79-6.16-2.37c-0.24-0.16-0.69-0.55-1.36-1.19c-0.67-0.63-1.28-1.14-1.84-1.54c-1.66-1.02-3.77-1.54-6.34-1.54c-2.57,0-4.7,0.61-6.4,1.84c-1.7,1.23-2.55,2.92-2.55,5.1c0,2.17,1.01,3.93,3.02,5.27c2.02,1.34,4.52,2.25,7.53,2.73c3,0.47,6.28,1.2,9.83,2.19c3.56,0.99,6.83,2.19,9.84,3.61c3,1.42,5.51,3.89,7.52,7.41c2.02,3.52,3.02,7.84,3.02,12.98s-1.03,9.66-3.08,13.57c-2.06,3.91-4.74,6.93-8.06,9.07c-6.4,4.19-13.23,6.28-20.5,6.28c-3.71,0-7.23-0.46-10.55-1.36c-3.32-0.9-6.01-2.03-8.06-3.37c-4.19-2.53-7.11-4.98-8.77-7.35L136.94,572.78z"/>
		<path class="st0" d="M230.62,564.02h36.5c1.82,0,3.18,0.06,4.09,0.18c0.91,0.12,1.96,0.49,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.46,8.77-4.38,9.72c-1.35,0.47-3.4,0.71-6.16,0.71h-46.92c-5.53,0-8.77-1.5-9.72-4.5c-0.48-1.27-0.71-3.28-0.71-6.05v-65.88c0-4.03,0.75-6.77,2.25-8.23c1.5-1.46,4.34-2.19,8.53-2.19h46.69c1.82,0,3.18,0.06,4.09,0.18s1.96,0.49,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.46,8.77-4.38,9.72c-1.35,0.47-3.4,0.71-6.16,0.71h-36.38v11.97h23.46c1.82,0,3.18,0.06,4.09,0.18c0.91,0.12,1.96,0.49,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.5,8.77-4.5,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-23.22V564.02z"/>
		<path class="st0" d="M311.14,564.02h36.5c1.82,0,3.18,0.06,4.09,0.18c0.91,0.12,1.96,0.49,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.46,8.77-4.38,9.72c-1.35,0.47-3.4,0.71-6.16,0.71h-46.92c-5.53,0-8.77-1.5-9.72-4.5c-0.48-1.27-0.71-3.28-0.71-6.05v-65.88c0-4.03,0.75-6.77,2.25-8.23c1.5-1.46,4.34-2.19,8.53-2.19h46.69c1.82,0,3.18,0.06,4.09,0.18s1.96,0.49,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.46,8.77-4.38,9.72c-1.35,0.47-3.4,0.71-6.16,0.71h-36.38v11.97h23.46c1.82,0,3.18,0.06,4.09,0.18c0.91,0.12,1.96,0.49,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.5,8.77-4.5,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-23.22V564.02z"/>
		<path class="st0" d="M381.23,498.01l21.92,0.12c11.45,0,21.52,4.13,30.22,12.38c8.69,8.26,13.03,18.41,13.03,30.45c0,12.05-4.25,22.38-12.74,30.99c-8.49,8.61-18.78,12.92-30.87,12.92h-21.69c-4.82,0-7.82-0.99-9.01-2.96c-0.95-1.66-1.42-4.19-1.42-7.58v-65.88c0-1.9,0.06-3.28,0.18-4.15c0.12-0.87,0.49-1.9,1.12-3.08C373.1,499.08,376.17,498.01,381.23,498.01z M418.56,557.56c4.58-4.23,6.87-9.54,6.87-15.94c0-6.4-2.23-11.75-6.69-16.05c-4.46-4.31-9.7-6.46-15.7-6.46h-11.37v44.79h11.49C408.84,563.89,413.98,561.78,418.56,557.56z"/>
	</g>
	<g>
		<path class="st1" d="M569.64,542.84c-2.01-3.51-4.52-5.98-7.52-7.4c-3.01-1.42-6.28-2.63-9.84-3.62c-3.55-0.98-6.83-1.72-9.83-2.19c-3.01-0.47-5.51-1.38-7.53-2.72c-2.01-1.35-3.02-3.1-3.02-5.28c0-2.17,0.85-3.87,2.55-5.09c1.7-1.23,3.83-1.84,6.4-1.84c2.56,0,4.68,0.51,6.34,1.54c0.55,0.4,1.16,0.91,1.83,1.54c0.67,0.63,1.13,1.03,1.37,1.19c2.44,1.58,4.5,2.37,6.16,2.37c2.84,0,5.6-1.98,8.29-5.93c1.9-2.76,2.85-4.93,2.85-6.51c0-1.59-1.23-3.52-3.68-5.81l-2.96-2.25c-1.5-1.27-4.21-2.51-8.12-3.74c-3.91-1.22-8.23-1.83-12.97-1.83c-8.93,0-15.98,2.58-21.16,7.76c-5.17,5.17-7.76,11.24-7.76,18.19c0,5.05,1.01,9.38,3.03,12.97c2.01,3.6,4.52,6.22,7.52,7.88c3,1.66,6.24,3.1,9.72,4.33c3.47,1.22,6.71,2.11,9.71,2.66c3.01,0.56,5.52,1.45,7.53,2.67c2.01,1.23,3.02,2.75,3.02,4.56c0,6.01-3.67,9.01-11.02,9.01c-1.74,0-3.63-0.61-5.69-1.84c-2.05-1.22-3.63-2.51-4.74-3.85c-3.95-3.95-7.03-5.92-9.24-5.92s-4.31,0.94-6.28,2.84c-3.4,3.32-5.09,5.98-5.09,8c0,2.01,1.02,4.28,3.07,6.81l1.07,1.31c1.66,2.37,4.58,4.82,8.77,7.34c2.05,1.35,4.74,2.47,8.06,3.38c3.32,0.91,6.83,1.36,10.54,1.36c7.27,0,14.1-2.09,20.5-6.28c3.32-2.13,6.01-5.15,8.06-9.06c2.06-3.91,3.08-8.44,3.08-13.57S571.66,546.36,569.64,542.84z"/>
		<path class="st1" d="M605.67,501.21c-1.03-2.93-4.31-4.39-9.84-4.39c-5.06,0-8.13,1.07-9.24,3.2c-0.64,1.19-1.01,2.24-1.13,3.14c-0.12,0.91-0.18,2.28-0.18,4.09v65.88c0,2.77,0.24,4.78,0.72,6.05c0.95,3,4.18,4.5,9.71,4.5c5.06,0,8.14-1.06,9.25-3.2c0.63-1.18,1-2.21,1.12-3.08s0.18-2.25,0.18-4.15v-65.88C606.26,504.6,606.06,502.55,605.67,501.21z"/>
		<path class="st1" d="M695.09,534.62c-0.94-2.05-3.55-3.16-7.82-3.32h-20.85c-2.37,0-4.27,0.36-5.69,1.07c-0.95,0.47-1.6,1.35-1.96,2.61c-0.35,1.26-0.53,2.94-0.53,5.03c0,2.1,0.16,3.76,0.48,4.98c0.31,1.23,0.98,2.16,2.01,2.78c1.03,0.64,2.77,0.96,5.21,0.96h9.37v12.91c-3.48,1.42-7.39,2.13-11.73,2.13c-6.01,0-11.38-2.39-16.12-7.17c-4.74-4.77-7.11-10.58-7.11-17.41c0-6.84,2.33-12.37,6.99-16.6c4.66-4.22,9.99-6.33,16-6.33c4.58,0,8.53,1.08,11.85,3.26c3.32,2.17,5.72,3.25,7.22,3.25c2.53,0,5.34-2.09,8.42-6.28c1.82-2.52,2.72-4.76,2.72-6.69s-1.06-3.7-3.19-5.28c-8.3-6.16-17.11-9.24-26.43-9.24c-12.01,0-22.43,4.21-31.28,12.62c-8.85,8.41-13.27,18.9-13.27,31.46s4.34,23.29,13.03,32.18c8.69,8.88,18.92,13.33,30.69,13.33c13.27,0,23.23-3.44,29.86-10.31c2.21-2.29,3.32-4.7,3.32-7.23v-26.07C696.28,538.34,695.88,536.12,695.09,534.62z"/>
		<path class="st1" d="M784.03,501.44c-0.32-1.1-0.81-1.93-1.48-2.49c-0.67-0.54-1.7-1.02-3.09-1.42c-1.38-0.39-3.19-0.59-5.44-0.59s-4.14,0.24-5.63,0.71c-1.51,0.48-2.63,1.41-3.38,2.79s-1.13,3.57-1.13,6.57v40.05c-5.61-7.26-16.75-22.23-33.41-44.9c-1.51-1.82-2.41-2.85-2.73-3.08c-0.55-0.56-1.52-1.05-2.9-1.49c-1.38-0.43-3.26-0.65-5.63-0.65s-4.3,0.24-5.81,0.71c-1.5,0.48-2.62,1.41-3.37,2.79c-0.76,1.38-1.13,3.57-1.13,6.57v66.12c0,1.82,0.06,3.2,0.18,4.15s0.49,2.02,1.12,3.2c1.11,2.14,4.11,3.2,9.01,3.2c5.06,0,8.14-1.06,9.24-3.2c0.64-1.18,1.01-2.21,1.13-3.08s0.18-2.25,0.18-4.15v-38.98c5.6,7.27,17.3,22.75,35.07,46.45c0.79,1.02,1.78,1.78,2.96,2.25c1.19,0.47,3.32,0.71,6.4,0.71c5.06,0,8.14-1.06,9.24-3.2c0.64-1.18,1.01-2.21,1.13-3.08s0.18-2.25,0.18-4.15v-65.76C784.74,504.72,784.5,502.71,784.03,501.44z"/>
		<path class="st1" d="M862.06,564.01c-1.19-0.63-2.24-1.01-3.14-1.13c-0.91-0.11-2.27-0.17-4.09-0.17h-36.5v-11.97h23.23c2.76,0,4.82-0.24,6.16-0.71c3-0.95,4.5-4.19,4.5-9.72c0-5.05-1.07-8.14-3.2-9.24c-1.18-0.63-2.23-1.01-3.14-1.13c-0.91-0.11-2.27-0.17-4.09-0.17h-23.46V517.8h36.38c2.76,0,4.82-0.24,6.16-0.71c2.92-0.95,4.39-4.19,4.39-9.72c0-5.06-1.07-8.14-3.2-9.24c-1.19-0.64-2.24-1.01-3.14-1.13c-0.91-0.12-2.27-0.18-4.09-0.18h-46.69c-4.19,0-7.03,0.73-8.53,2.2c-1.5,1.46-2.25,4.2-2.25,8.23v65.88c0,2.77,0.24,4.78,0.71,6.05c0.95,3,4.19,4.5,9.72,4.5h46.92c2.76,0,4.82-0.24,6.16-0.71c2.92-0.95,4.39-4.19,4.39-9.72C865.26,568.2,864.19,565.12,862.06,564.01z"/>
		<path class="st1" d="M944.35,568.99c-3.63-8.22-6.31-14.42-8.05-18.61c5.92-5.76,8.89-13.11,8.89-22.04c0-5.13-1.03-9.79-3.09-13.98c-2.05-4.19-4.66-7.5-7.82-9.95c-6.55-5.06-13.31-7.59-20.26-7.59h-25.6c-5.05,0-8.13,1.07-9.24,3.2c-0.63,1.19-1.01,2.24-1.12,3.14c-0.12,0.91-0.18,2.28-0.18,4.09v65.77c0,2.76,0.24,4.82,0.71,6.16c0.95,2.92,4.19,4.38,9.72,4.38c5.05,0,8.13-1.06,9.24-3.2c0.63-1.18,1.01-2.23,1.12-3.14c0.13-0.91,0.18-2.27,0.18-4.09v-13.39h14.93l3.68-0.23c5.37,12.79,8.45,19.94,9.24,21.44c0.47,0.79,1.2,1.57,2.19,2.32s2.25,1.12,3.8,1.12c1.54,0,3.57-0.55,6.1-1.66c4.89-2.05,7.34-4.58,7.34-7.58C946.13,573.88,945.54,571.83,944.35,568.99z M920.89,536.16c-2.29,1.74-4.58,2.61-6.87,2.61h-15.17V517.8h14.93c2.45,0,4.82,0.89,7.11,2.66c2.3,1.78,3.44,4.41,3.44,7.88C924.33,531.82,923.19,534.43,920.89,536.16z"/>
	</g>
</g>
<path class="st0" d="M1009.44,463.97c-0.01-0.02-0.02-0.04-0.04-0.06c-6.57-12.07-14.63-23.19-23.89-33.06c-9.03-9.63-19.22-18.08-30.31-25.09c-21.24-13.42-45.8-21.54-71.99-22.49H205.02c-28.34,0.93-54.68,9.01-77.27,22.49c-25.45,15.18-46.14,37.2-59.63,63.53c-11.06,21.58-17.26,46.06-17.26,72.04c0,28.1,7.24,54.49,19.9,77.26c12.72,22.87,30.9,42.09,52.69,55.75c22.65,14.21,49.22,22.39,77.59,22.39h677.91c28.37,0,54.93-8.18,77.6-22.39c0.04-0.03,0.09-0.05,0.13-0.09c21.84-13.71,40.02-33.03,52.72-55.98c12.56-22.7,19.74-48.97,19.74-76.94C1029.14,513.41,1021.97,486.96,1009.44,463.97z M944.35,568.99c1.19,2.84,1.78,4.89,1.78,6.16c0,3-2.45,5.53-7.34,7.58c-2.53,1.11-4.56,1.66-6.1,1.66c-1.55,0-2.81-0.37-3.8-1.12s-1.72-1.53-2.19-2.32c-0.79-1.5-3.87-8.65-9.24-21.44l-3.68,0.23h-14.93v13.39c0,1.82-0.05,3.18-0.18,4.09c-0.11,0.91-0.49,1.96-1.12,3.14c-1.11,2.14-4.19,3.2-9.24,3.2c-5.53,0-8.77-1.46-9.72-4.38c-0.47-1.34-0.71-3.4-0.71-6.16v-65.77c0-1.81,0.06-3.18,0.18-4.09c0.11-0.9,0.49-1.95,1.12-3.14c1.11-2.13,4.19-3.2,9.24-3.2h25.6c6.95,0,13.71,2.53,20.26,7.59c3.16,2.45,5.77,5.76,7.82,9.95c2.06,4.19,3.09,8.85,3.09,13.98c0,8.93-2.97,16.28-8.89,22.04C938.04,554.57,940.72,560.77,944.35,568.99z M841.79,529.77c1.82,0,3.18,0.06,4.09,0.17c0.91,0.12,1.96,0.5,3.14,1.13c2.13,1.1,3.2,4.19,3.2,9.24c0,5.53-1.5,8.77-4.5,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-23.23v11.97h36.5c1.82,0,3.18,0.06,4.09,0.17c0.9,0.12,1.95,0.5,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.47,8.77-4.39,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-46.92c-5.53,0-8.77-1.5-9.72-4.5c-0.47-1.27-0.71-3.28-0.71-6.05v-65.88c0-4.03,0.75-6.77,2.25-8.23c1.5-1.47,4.34-2.2,8.53-2.2h46.69c1.82,0,3.18,0.06,4.09,0.18c0.9,0.12,1.95,0.49,3.14,1.13c2.13,1.1,3.2,4.18,3.2,9.24c0,5.53-1.47,8.77-4.39,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-36.38v11.97H841.79z M784.74,507.49v65.76c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.13,3.08c-1.1,2.14-4.18,3.2-9.24,3.2c-3.08,0-5.21-0.24-6.4-0.71c-1.18-0.47-2.17-1.23-2.96-2.25c-17.77-23.7-29.47-39.18-35.07-46.45v38.98c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.13,3.08c-1.1,2.14-4.18,3.2-9.24,3.2c-4.9,0-7.9-1.06-9.01-3.2c-0.63-1.18-1-2.25-1.12-3.2s-0.18-2.33-0.18-4.15v-66.12c0-3,0.37-5.19,1.13-6.57c0.75-1.38,1.87-2.31,3.37-2.79c1.51-0.47,3.44-0.71,5.81-0.71s4.25,0.22,5.63,0.65c1.38,0.44,2.35,0.93,2.9,1.49c0.32,0.23,1.22,1.26,2.73,3.08c16.66,22.67,27.8,37.64,33.41,44.9v-40.05c0-3,0.38-5.19,1.13-6.57s1.87-2.31,3.38-2.79c1.49-0.47,3.38-0.71,5.63-0.71s4.06,0.2,5.44,0.59c1.39,0.4,2.42,0.88,3.09,1.42c0.67,0.56,1.16,1.39,1.48,2.49C784.5,502.71,784.74,504.72,784.74,507.49z M647.46,556.6c4.74,4.78,10.11,7.17,16.12,7.17c4.34,0,8.25-0.71,11.73-2.13v-12.91h-9.37c-2.44,0-4.18-0.32-5.21-0.96c-1.03-0.62-1.7-1.55-2.01-2.78c-0.32-1.22-0.48-2.88-0.48-4.98c0-2.09,0.18-3.77,0.53-5.03c0.36-1.26,1.01-2.14,1.96-2.61c1.42-0.71,3.32-1.07,5.69-1.07h20.85c4.27,0.16,6.88,1.27,7.82,3.32c0.79,1.5,1.19,3.72,1.19,6.64v26.07c0,2.53-1.11,4.94-3.32,7.23c-6.63,6.87-16.59,10.31-29.86,10.31c-11.77,0-22-4.45-30.69-13.33c-8.69-8.89-13.03-19.62-13.03-32.18s4.42-23.05,13.27-31.46c8.85-8.41,19.27-12.62,31.28-12.62c9.32,0,18.13,3.08,26.43,9.24c2.13,1.58,3.19,3.35,3.19,5.28s-0.9,4.17-2.72,6.69c-3.08,4.19-5.89,6.28-8.42,6.28c-1.5,0-3.9-1.08-7.22-3.25c-3.32-2.18-7.27-3.26-11.85-3.26c-6.01,0-11.34,2.11-16,6.33c-4.66,4.23-6.99,9.76-6.99,16.6C640.35,546.02,642.72,551.83,647.46,556.6z M606.26,507.37v65.88c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.12,3.08c-1.11,2.14-4.19,3.2-9.25,3.2c-5.53,0-8.76-1.5-9.71-4.5c-0.48-1.27-0.72-3.28-0.72-6.05v-65.88c0-1.81,0.06-3.18,0.18-4.09c0.12-0.9,0.49-1.95,1.13-3.14c1.11-2.13,4.18-3.2,9.24-3.2c5.53,0,8.81,1.46,9.84,4.39C606.06,502.55,606.26,504.6,606.26,507.37z M548.55,551.73c-2.01-1.22-4.52-2.11-7.53-2.67c-3-0.55-6.24-1.44-9.71-2.66c-3.48-1.23-6.72-2.67-9.72-4.33c-3-1.66-5.51-4.28-7.52-7.88c-2.02-3.59-3.03-7.92-3.03-12.97c0-6.95,2.59-13.02,7.76-18.19c5.18-5.18,12.23-7.76,21.16-7.76c4.74,0,9.06,0.61,12.97,1.83c3.91,1.23,6.62,2.47,8.12,3.74l2.96,2.25c2.45,2.29,3.68,4.22,3.68,5.81c0,1.58-0.95,3.75-2.85,6.51c-2.69,3.95-5.45,5.93-8.29,5.93c-1.66,0-3.72-0.79-6.16-2.37c-0.24-0.16-0.7-0.56-1.37-1.19c-0.67-0.63-1.28-1.14-1.83-1.54c-1.66-1.03-3.78-1.54-6.34-1.54c-2.57,0-4.7,0.61-6.4,1.84c-1.7,1.22-2.55,2.92-2.55,5.09c0,2.18,1.01,3.93,3.02,5.28c2.02,1.34,4.52,2.25,7.53,2.72c3,0.47,6.28,1.21,9.83,2.19c3.56,0.99,6.83,2.2,9.84,3.62c3,1.42,5.51,3.89,7.52,7.4c2.02,3.52,3.02,7.85,3.02,12.98s-1.02,9.66-3.08,13.57c-2.05,3.91-4.74,6.93-8.06,9.06c-6.4,4.19-13.23,6.28-20.5,6.28c-3.71,0-7.22-0.45-10.54-1.36c-3.32-0.91-6.01-2.03-8.06-3.38c-4.19-2.52-7.11-4.97-8.77-7.34l-1.07-1.31c-2.05-2.53-3.07-4.8-3.07-6.81c0-2.02,1.69-4.68,5.09-8c1.97-1.9,4.07-2.84,6.28-2.84s5.29,1.97,9.24,5.92c1.11,1.34,2.69,2.63,4.74,3.85c2.06,1.23,3.95,1.84,5.69,1.84c7.35,0,11.02-3,11.02-9.01C551.57,554.48,550.56,552.96,548.55,551.73z M77.74,584.87c-4.65-13.65-7.18-28.29-7.18-43.54c0-16.2,2.87-31.72,8.16-46.1c18.71-50.84,67.61-87.44,126.31-89.47c0.09-0.01,0.19-0.01,0.27-0.01h272.65v268.5H201.04C144.05,674.25,95.48,636.85,77.74,584.87z"/>
<path class="st1" d="M569.64,542.84c2.02,3.52,3.02,7.85,3.02,12.98s-1.02,9.66-3.08,13.57c-2.05,3.91-4.74,6.93-8.06,9.06c-6.4,4.19-13.23,6.28-20.5,6.28c-3.71,0-7.22-0.45-10.54-1.36c-3.32-0.91-6.01-2.03-8.06-3.38c-4.19-2.52-7.11-4.97-8.77-7.34l-1.07-1.31c-2.05-2.53-3.07-4.8-3.07-6.81c0-2.02,1.69-4.68,5.09-8c1.97-1.9,4.07-2.84,6.28-2.84s5.29,1.97,9.24,5.92c1.11,1.34,2.69,2.63,4.74,3.85c2.06,1.23,3.95,1.84,5.69,1.84c7.35,0,11.02-3,11.02-9.01c0-1.81-1.01-3.33-3.02-4.56c-2.01-1.22-4.52-2.11-7.53-2.67c-3-0.55-6.24-1.44-9.71-2.66c-3.48-1.23-6.72-2.67-9.72-4.33c-3-1.66-5.51-4.28-7.52-7.88c-2.02-3.59-3.03-7.92-3.03-12.97c0-6.95,2.59-13.02,7.76-18.19c5.18-5.18,12.23-7.76,21.16-7.76c4.74,0,9.06,0.61,12.97,1.83c3.91,1.23,6.62,2.47,8.12,3.74l2.96,2.25c2.45,2.29,3.68,4.22,3.68,5.81c0,1.58-0.95,3.75-2.85,6.51c-2.69,3.95-5.45,5.93-8.29,5.93c-1.66,0-3.72-0.79-6.16-2.37c-0.24-0.16-0.7-0.56-1.37-1.19c-0.67-0.63-1.28-1.14-1.83-1.54c-1.66-1.03-3.78-1.54-6.34-1.54c-2.57,0-4.7,0.61-6.4,1.84c-1.7,1.22-2.55,2.92-2.55,5.09c0,2.18,1.01,3.93,3.02,5.28c2.02,1.34,4.52,2.25,7.53,2.72c3,0.47,6.28,1.21,9.83,2.19c3.56,0.99,6.83,2.2,9.84,3.62C565.12,536.86,567.63,539.33,569.64,542.84z"/>
<path class="st1" d="M605.67,501.21c0.39,1.34,0.59,3.39,0.59,6.16v65.88c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.12,3.08c-1.11,2.14-4.19,3.2-9.25,3.2c-5.53,0-8.76-1.5-9.71-4.5c-0.48-1.27-0.72-3.28-0.72-6.05v-65.88c0-1.81,0.06-3.18,0.18-4.09c0.12-0.9,0.49-1.95,1.13-3.14c1.11-2.13,4.18-3.2,9.24-3.2C601.36,496.82,604.64,498.28,605.67,501.21z"/>
<path class="st1" d="M695.09,534.62c0.79,1.5,1.19,3.72,1.19,6.64v26.07c0,2.53-1.11,4.94-3.32,7.23c-6.63,6.87-16.59,10.31-29.86,10.31c-11.77,0-22-4.45-30.69-13.33c-8.69-8.89-13.03-19.62-13.03-32.18s4.42-23.05,13.27-31.46c8.85-8.41,19.27-12.62,31.28-12.62c9.32,0,18.13,3.08,26.43,9.24c2.13,1.58,3.19,3.35,3.19,5.28s-0.9,4.17-2.72,6.69c-3.08,4.19-5.89,6.28-8.42,6.28c-1.5,0-3.9-1.08-7.22-3.25c-3.32-2.18-7.27-3.26-11.85-3.26c-6.01,0-11.34,2.11-16,6.33c-4.66,4.23-6.99,9.76-6.99,16.6c0,6.83,2.37,12.64,7.11,17.41c4.74,4.78,10.11,7.17,16.12,7.17c4.34,0,8.25-0.71,11.73-2.13v-12.91h-9.37c-2.44,0-4.18-0.32-5.21-0.96c-1.03-0.62-1.7-1.55-2.01-2.78c-0.32-1.22-0.48-2.88-0.48-4.98c0-2.09,0.18-3.77,0.53-5.03c0.36-1.26,1.01-2.14,1.96-2.61c1.42-0.71,3.32-1.07,5.69-1.07h20.85C691.54,531.46,694.15,532.57,695.09,534.62z"/>
<path class="st1" d="M784.03,501.44c0.47,1.27,0.71,3.28,0.71,6.05v65.76c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.13,3.08c-1.1,2.14-4.18,3.2-9.24,3.2c-3.08,0-5.21-0.24-6.4-0.71c-1.18-0.47-2.17-1.23-2.96-2.25c-17.77-23.7-29.47-39.18-35.07-46.45v38.98c0,1.9-0.06,3.28-0.18,4.15s-0.49,1.9-1.13,3.08c-1.1,2.14-4.18,3.2-9.24,3.2c-4.9,0-7.9-1.06-9.01-3.2c-0.63-1.18-1-2.25-1.12-3.2s-0.18-2.33-0.18-4.15v-66.12c0-3,0.37-5.19,1.13-6.57c0.75-1.38,1.87-2.31,3.37-2.79c1.51-0.47,3.44-0.71,5.81-0.71s4.25,0.22,5.63,0.65c1.38,0.44,2.35,0.93,2.9,1.49c0.32,0.23,1.22,1.26,2.73,3.08c16.66,22.67,27.8,37.64,33.41,44.9v-40.05c0-3,0.38-5.19,1.13-6.57s1.87-2.31,3.38-2.79c1.49-0.47,3.38-0.71,5.63-0.71s4.06,0.2,5.44,0.59c1.39,0.4,2.42,0.88,3.09,1.42C783.22,499.51,783.71,500.34,784.03,501.44z"/>
<path class="st1" d="M818.33,517.8v11.97h23.46c1.82,0,3.18,0.06,4.09,0.17c0.91,0.12,1.96,0.5,3.14,1.13c2.13,1.1,3.2,4.19,3.2,9.24c0,5.53-1.5,8.77-4.5,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-23.23v11.97h36.5c1.82,0,3.18,0.06,4.09,0.17c0.9,0.12,1.95,0.5,3.14,1.13c2.13,1.11,3.2,4.19,3.2,9.24c0,5.53-1.47,8.77-4.39,9.72c-1.34,0.47-3.4,0.71-6.16,0.71h-46.92c-5.53,0-8.77-1.5-9.72-4.5c-0.47-1.27-0.71-3.28-0.71-6.05v-65.88c0-4.03,0.75-6.77,2.25-8.23c1.5-1.47,4.34-2.2,8.53-2.2h46.69c1.82,0,3.18,0.06,4.09,0.18c0.9,0.12,1.95,0.49,3.14,1.13c2.13,1.1,3.2,4.18,3.2,9.24c0,5.53-1.47,8.77-4.39,9.72c-1.34,0.47-3.4,0.71-6.16,0.71H818.33z"/>'''


@dataclass
class CardConfig:
    """Configuration for card generation."""
    qr_size: int
    num_words: int
    title: str = "SEED SIGNER"
    border_color: str = "#FF7300"
    width: float = 53.98
    height: float = 85.6
    border_radius: float = 3.0
    border_width: float = 1.2
    padding: float = 3.0


def generate_front_svg(config: CardConfig) -> str:
    """Generate the front side SVG with QR grid template."""

    w = config.width
    h = config.height
    br = config.border_radius
    bw = config.border_width
    pad = config.padding
    margin = 2  # Margin around the card to prevent border clipping

    header_height = 6
    fingerprint_height = 5
    warning_height = 3
    notes_height = 13

    qr_size = config.qr_size
    label_size = 3

    qr_area_top = header_height + fingerprint_height + pad * 1.5
    available_height = h - qr_area_top - warning_height - notes_height - pad
    available_width = w - pad * 2 - label_size

    qr_grid_size = min(available_height - label_size, available_width)
    cell_size = qr_grid_size / qr_size

    qr_left = (w - qr_grid_size) / 2 - label_size
    qr_top = qr_area_top + label_size

    # Total SVG size includes margin, but card stays credit card size
    svg_w = w + margin * 2
    svg_h = h + margin * 2

    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}mm" height="{svg_h}mm">')
    svg_parts.append(f'  <g transform="translate({margin}, {margin})">')
    svg_parts.append('  <defs>')
    svg_parts.append('    <style>')
    svg_parts.append('      .title-text { font-family: Arial, Helvetica, sans-serif; font-weight: bold; fill: white; }')
    svg_parts.append('      .label-text { font-family: Arial, Helvetica, sans-serif; fill: #666; }')
    svg_parts.append('      .warning-text { font-family: Arial, Helvetica, sans-serif; font-size: 1.6px; fill: #666; }')
    svg_parts.append('      .notes-label { font-family: Arial, Helvetica, sans-serif; font-size: 2px; font-weight: bold; fill: #333; }')
    svg_parts.append('      .grid-line { stroke: #888; stroke-width: 0.15; stroke-dasharray: 0.5,0.5; }')
    svg_parts.append('      .block-line { stroke: black; stroke-width: 0.4; }')
    svg_parts.append('      .finder-pattern { fill: black; }')
    svg_parts.append('      .finder-inner { fill: white; }')
    svg_parts.append('      .finder-core { fill: black; }')
    svg_parts.append('    </style>')
    svg_parts.append('  </defs>')
    svg_parts.append('')
    svg_parts.append('  <!-- Card background -->')
    svg_parts.append(f'  <rect x="0" y="{header_height/2}" width="{w}" height="{h - header_height/2}" rx="{br}" fill="white" stroke="{config.border_color}" stroke-width="{bw}"/>')
    svg_parts.append('')
    svg_parts.append('  <!-- SeedSigner logo banner -->')

    # Embed the logo from file
    logo_content = get_logo_svg_content()
    logo_width = 22
    logo_height = 7
    logo_x = (w - logo_width) / 2
    logo_y = -0.5

    if logo_content:
        # White background slightly smaller than logo to avoid gap with border
        bg_inset = 0.8
        svg_parts.append(f'  <rect x="{logo_x + bg_inset}" y="{logo_y + bg_inset}" width="{logo_width - bg_inset*2}" height="{logo_height - bg_inset*2}" fill="white"/>')
        svg_parts.append(f'  <svg x="{logo_x}" y="{logo_y}" width="{logo_width}" height="{logo_height}" viewBox="30 380 1020 320" preserveAspectRatio="xMidYMid meet">')
        svg_parts.append(logo_content)
        svg_parts.append('  </svg>')
    else:
        pill_y = -(header_height/2 - 0.5)
        pill_h = header_height - 1
        pill_rx = pill_h / 2
        box_y = -(header_height/2 - 1)
        box_h = header_height - 2
        box_rx = box_h / 2
        svg_parts.append(f'  <g transform="translate({w/2}, {header_height/2})">')
        svg_parts.append(f'    <rect x="-16" y="{pill_y}" width="32" height="{pill_h}" rx="{pill_rx}" fill="{config.border_color}"/>')
        svg_parts.append(f'    <rect x="-15" y="{box_y}" width="13" height="{box_h}" rx="{box_rx}" fill="white"/>')
        svg_parts.append(f'    <text x="-8.5" y="1.2" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-weight="bold" font-size="3.5" fill="{config.border_color}">SEED</text>')
        svg_parts.append('    <text x="7" y="1.2" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-weight="bold" font-size="3.5" fill="white">SIGNER</text>')
        svg_parts.append('  </g>')

    svg_parts.append('')
    svg_parts.append('  <!-- Fingerprint field -->')
    svg_parts.append(f'  <rect x="{pad}" y="{header_height + pad}" width="{w - pad*2}" height="{fingerprint_height}" rx="2.5" fill="white" stroke="black" stroke-width="0.4"/>')
    svg_parts.append('  <!-- Fingerprint icon -->')
    # Icon is ~425 units tall in original, scaled by 0.0087 = ~3.7mm. Center it in the fingerprint_height box.
    icon_y_offset = (fingerprint_height - 5.5) / 2
    svg_parts.append(f'  <g transform="translate({pad + 1.5}, {header_height + pad + icon_y_offset}) scale(0.0087)">')
    svg_parts.append('    <path fill="black" d="M259.476,280.364V247.5c0-12.958-10.542-23.5-23.5-23.5s-23.5,10.542-23.5,23.5v29.672c0,35.757-13.173,70.087-37.094,96.665l-32.981,36.646c-2.771,3.079-2.521,7.821,0.558,10.593c3.078,2.771,7.82,2.521,10.592-0.558l32.981-36.646c26.403-29.338,40.944-67.231,40.944-106.7V247.5c0-4.687,3.813-8.5,8.5-8.5s8.5,3.813,8.5,8.5v32.864c0,44.003-16.301,86.167-45.901,118.727l-32.149,35.364c-2.786,3.064-2.56,7.809,0.505,10.595c1.437,1.307,3.242,1.95,5.042,1.95c2.04,0,4.072-0.827,5.552-2.455l32.148-35.364C241.789,373.854,259.476,328.106,259.476,280.364z"/>')
    svg_parts.append('    <path fill="black" d="M291.476,247.5c0-30.603-24.897-55.5-55.5-55.5s-55.5,24.897-55.5,55.5v29.672c0,27.839-10.256,54.566-28.879,75.258l-23.447,26.053c-2.771,3.079-2.521,7.821,0.558,10.593c3.079,2.771,7.82,2.519,10.592-0.558l23.447-26.053c21.106-23.451,32.73-53.742,32.73-85.293V247.5c0-22.332,18.168-40.5,40.5-40.5c22.332,0,40.5,18.168,40.5,40.5v32.864c0,51.979-19.256,101.789-54.223,140.252l-27.125,29.839c-2.787,3.064-2.561,7.809,0.504,10.595c1.437,1.307,3.242,1.95,5.042,1.95c2.04,0,4.072-0.827,5.552-2.455l27.126-29.839c37.481-41.23,58.123-94.622,58.123-150.342V247.5z"/>')
    svg_parts.append('    <path fill="black" d="M323.476,247.5c0-48.248-39.252-87.5-87.5-87.5s-87.5,39.252-87.5,87.5v29.672c0,19.92-7.339,39.045-20.665,53.851l-21.112,23.458c-2.771,3.079-2.521,7.821,0.558,10.593c3.078,2.771,7.821,2.519,10.592-0.558l21.112-23.458c15.809-17.565,24.515-40.254,24.515-63.886V247.5c0-39.977,32.523-72.5,72.5-72.5s72.5,32.523,72.5,72.5v32.864c0,59.958-22.212,117.412-62.545,161.777l-7.507,8.258c-2.786,3.065-2.56,7.809,0.505,10.595c1.437,1.306,3.243,1.95,5.042,1.95c2.04,0,4.072-0.827,5.552-2.455l7.506-8.258c42.848-47.133,66.446-108.169,66.446-171.867V247.5z"/>')
    svg_parts.append('  </g>')
    svg_parts.append('')
    svg_parts.append('  <!-- QR Code Grid -->')

    # Draw grid lines
    for i in range(qr_size + 1):
        x = qr_left + label_size + i * cell_size
        y1 = qr_top
        y2 = qr_top + qr_grid_size
        svg_parts.append(f'  <line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" class="grid-line"/>')

    for i in range(qr_size + 1):
        y = qr_top + i * cell_size
        x1 = qr_left + label_size
        x2 = qr_left + label_size + qr_grid_size
        svg_parts.append(f'  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" class="grid-line"/>')

    # Draw block divider lines
    block_size = 7 if qr_size == 21 else 5
    num_blocks = math.ceil(qr_size / block_size)

    for i in range(num_blocks + 1):
        pos = min(i * block_size, qr_size)
        x = qr_left + label_size + pos * cell_size
        y = qr_top + pos * cell_size
        svg_parts.append(f'  <line x1="{x}" y1="{qr_top}" x2="{x}" y2="{qr_top + qr_grid_size}" class="block-line"/>')
        svg_parts.append(f'  <line x1="{qr_left + label_size}" y1="{y}" x2="{qr_left + label_size + qr_grid_size}" y2="{y}" class="block-line"/>')

    # Column labels
    for i in range(num_blocks):
        block_start = i * block_size
        block_end = min((i + 1) * block_size, qr_size)
        block_width = (block_end - block_start) * cell_size
        col_x = qr_left + label_size + block_start * cell_size
        col_center = col_x + block_width / 2
        svg_parts.append(f'  <text x="{col_center}" y="{qr_top - label_size * 0.3}" text-anchor="middle" class="label-text" font-size="{label_size * 0.7}">{i + 1}</text>')

    # Row labels
    row_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(num_blocks):
        block_start = i * block_size
        block_end = min((i + 1) * block_size, qr_size)
        block_height = (block_end - block_start) * cell_size
        row_y = qr_top + block_start * cell_size
        row_center = row_y + block_height / 2
        svg_parts.append(f'  <text x="{qr_left + label_size/2}" y="{row_center + label_size * 0.2}" text-anchor="middle" class="label-text" font-size="{label_size * 0.7}">{row_labels[i]}</text>')

    # Draw finder patterns
    def draw_finder_pattern(cx, cy):
        patterns = []
        x = qr_left + label_size + cx * cell_size
        y = qr_top + cy * cell_size
        s = cell_size
        patterns.append(f'  <rect x="{x}" y="{y}" width="{7*s}" height="{7*s}" class="finder-pattern"/>')
        patterns.append(f'  <rect x="{x + s}" y="{y + s}" width="{5*s}" height="{5*s}" class="finder-inner"/>')
        patterns.append(f'  <rect x="{x + 2*s}" y="{y + 2*s}" width="{3*s}" height="{3*s}" class="finder-core"/>')
        return patterns

    svg_parts.extend(draw_finder_pattern(0, 0))
    svg_parts.extend(draw_finder_pattern(qr_size - 7, 0))
    svg_parts.extend(draw_finder_pattern(0, qr_size - 7))

    # Alignment pattern for larger QR codes (5x5 pattern with 3x3 white and 1x1 black center)
    if qr_size >= 25:
        # Alignment pattern center position (0-indexed cell)
        align_center = qr_size - 7  # For 25x25, this is cell 18
        ax = qr_left + label_size + align_center * cell_size
        ay = qr_top + align_center * cell_size
        s = cell_size
        # Draw from top-left of the 5x5 pattern (center - 2 cells)
        svg_parts.append(f'  <rect x="{ax - 2*s}" y="{ay - 2*s}" width="{5*s}" height="{5*s}" fill="black"/>')
        svg_parts.append(f'  <rect x="{ax - s}" y="{ay - s}" width="{3*s}" height="{3*s}" fill="white"/>')
        svg_parts.append(f'  <rect x="{ax}" y="{ay}" width="{s}" height="{s}" fill="black"/>')

    # Warning text
    warning_y = qr_top + qr_grid_size + 1
    svg_parts.append(f'  <text x="{w/2}" y="{warning_y + 1.5}" text-anchor="middle" class="warning-text">Never scan seed QR into a computer that connects to the internet.</text>')

    # Notes section
    notes_y = h - notes_height - pad
    svg_parts.append(f'  <rect x="{pad}" y="{notes_y}" width="{w - pad*2}" height="{notes_height}" rx="1" fill="white" stroke="black" stroke-width="0.4"/>')
    svg_parts.append(f'  <text x="{pad + 2}" y="{notes_y + 2.5}" class="notes-label">Notes:</text>')

    svg_parts.append('  </g>')
    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def generate_back_svg(config: CardConfig) -> str:
    """Generate the back side SVG with word list."""

    w = config.width
    h = config.height
    br = config.border_radius
    bw = config.border_width
    pad = config.padding
    margin = 2  # Margin around the card to prevent border clipping

    header_height = 6

    # Total SVG size includes margin, but card stays credit card size
    svg_w = w + margin * 2
    svg_h = h + margin * 2

    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}mm" height="{svg_h}mm">')
    svg_parts.append(f'  <g transform="translate({margin}, {margin})">')
    svg_parts.append('  <defs>')
    svg_parts.append('    <style>')
    svg_parts.append('      .word-num { font-family: Arial, Helvetica, sans-serif; font-size: 2.2px; fill: black; }')
    svg_parts.append('      .word-line { stroke: black; stroke-width: 0.3; }')
    svg_parts.append('      .section-title { font-family: Arial, Helvetica, sans-serif; font-size: 2.5px; font-weight: bold; fill: #333; }')
    svg_parts.append('    </style>')
    svg_parts.append('  </defs>')
    svg_parts.append('')
    svg_parts.append('  <!-- Card background -->')
    svg_parts.append(f'  <rect x="0" y="{header_height/2}" width="{w}" height="{h - header_height/2}" rx="{br}" fill="white" stroke="{config.border_color}" stroke-width="{bw}"/>')
    svg_parts.append('')
    svg_parts.append('  <!-- SeedSigner logo banner -->')

    # Embed the logo
    logo_content = get_logo_svg_content()
    logo_width = 22
    logo_height = 7
    logo_x = (w - logo_width) / 2
    logo_y = -0.5

    if logo_content:
        # White background slightly smaller than logo to avoid gap with border
        bg_inset = 0.8
        svg_parts.append(f'  <rect x="{logo_x + bg_inset}" y="{logo_y + bg_inset}" width="{logo_width - bg_inset*2}" height="{logo_height - bg_inset*2}" fill="white"/>')
        svg_parts.append(f'  <svg x="{logo_x}" y="{logo_y}" width="{logo_width}" height="{logo_height}" viewBox="30 380 1020 320" preserveAspectRatio="xMidYMid meet">')
        svg_parts.append(logo_content)
        svg_parts.append('  </svg>')

    svg_parts.append('')
    svg_parts.append('  <!-- Section Title -->')
    svg_parts.append(f'  <text x="{w/2}" y="{header_height + pad + 3}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="5" font-weight="bold" fill="{config.border_color}">SEED WORDS</text>')

    svg_parts.append('')
    svg_parts.append('  <!-- Word List -->')

    words_per_column = 12
    num_columns = 2 if config.num_words == 24 else 1

    word_area_top = header_height + pad + 6
    word_area_height = h - word_area_top - pad - 2
    word_spacing = word_area_height / words_per_column

    if num_columns == 1:
        col_width = w - pad * 4
        col_start = pad * 2
    else:
        col_width = (w - pad * 3) / 2
        col_start = pad

    line_width = col_width * 0.65

    for col in range(num_columns):
        col_x = col_start + col * (col_width + pad)

        for i in range(words_per_column):
            word_num = col * 12 + i + 1
            y = word_area_top + i * word_spacing + word_spacing * 0.6
            svg_parts.append(f'  <text x="{col_x + 3}" y="{y}" class="word-num">{word_num}:</text>')
            line_x = col_x + 8
            svg_parts.append(f'  <line x1="{line_x}" y1="{y + 0.5}" x2="{line_x + line_width}" y2="{y + 0.5}" class="word-line"/>')

    svg_parts.append('  </g>')
    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def generate_pdf(front_svg: str, back_svg: str, output_filename: str, config: CardConfig):
    """Generate a two-page PDF from front and back SVG content."""
    try:
        import cairosvg
        from pypdf import PdfWriter, PdfReader
    except ImportError as e:
        print("Error: PDF generation requires 'cairosvg' and 'pypdf' packages.")
        print("Install them with: pip install cairosvg pypdf")
        return False

    # Convert SVGs to PDF bytes
    front_pdf = cairosvg.svg2pdf(bytestring=front_svg.encode('utf-8'))
    back_pdf = cairosvg.svg2pdf(bytestring=back_svg.encode('utf-8'))

    # Merge into a single PDF
    writer = PdfWriter()

    # Add front page
    front_reader = PdfReader(io.BytesIO(front_pdf))
    writer.add_page(front_reader.pages[0])

    # Add back page
    back_reader = PdfReader(io.BytesIO(back_pdf))
    writer.add_page(back_reader.pages[0])

    # Write combined PDF
    with open(output_filename, 'wb') as f:
        writer.write(f)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="""
Generates front and back SVG templates for SeedQR backup cards.

Examples:
    python template_generator.py 21 12
    python template_generator.py 25 24 --title "My Wallet" --color "#ff6600"
    python template_generator.py 21 12 --pdf  # Also generates a two-page PDF
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('qr_size', type=int, choices=[21, 25, 29],
                        help="QR code size: 21 (small), 25 (medium), 29 (large)")
    parser.add_argument('num_words', type=int, choices=[12, 24],
                        help="Number of seed words: 12 or 24")
    parser.add_argument('-t', '--title', type=str, default="SEED SIGNER",
                        help="Card title (default: 'SEED SIGNER')")
    parser.add_argument('-c', '--color', type=str, default="#FF7300",
                        help="Border/header color (default: '#FF7300' SeedSigner orange)")
    parser.add_argument('-o', '--output', type=str, default=None,
                        help="Output filename prefix (default: based on size/words)")
    parser.add_argument('--pdf', action='store_true',
                        help="Also generate a two-page PDF file")

    args = parser.parse_args()

    config = CardConfig(
        qr_size=args.qr_size,
        num_words=args.num_words,
        title=args.title,
        border_color=args.color,
    )

    front_svg = generate_front_svg(config)
    back_svg = generate_back_svg(config)

    if args.output:
        front_filename = f"{args.output}_front.svg"
        back_filename = f"{args.output}_back.svg"
    else:
        front_filename = f"seedqr_template_{args.num_words}words_{args.qr_size}x{args.qr_size}_front.svg"
        back_filename = f"seedqr_template_{args.num_words}words_{args.qr_size}x{args.qr_size}_back.svg"

    with open(front_filename, 'w') as f:
        f.write(front_svg)
    print(f"Created: {front_filename}")

    with open(back_filename, 'w') as f:
        f.write(back_svg)
    print(f"Created: {back_filename}")

    # Generate PDF if requested
    if args.pdf:
        if args.output:
            pdf_filename = f"{args.output}.pdf"
        else:
            pdf_filename = f"seedqr_template_{args.num_words}words_{args.qr_size}x{args.qr_size}.pdf"

        if generate_pdf(front_svg, back_svg, pdf_filename, config):
            print(f"Created: {pdf_filename}")


if __name__ == "__main__":
    main()
