/*------------------------------------------------------------------------------
 * Copyright (c) 2017-2019
 *     Michael Theall (mtheall)
 *
 * This file is part of tex3ds.
 *
 * tex3ds is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * tex3ds is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with tex3ds.  If not, see <http://www.gnu.org/licenses/>.
 *----------------------------------------------------------------------------*/

// this file has obviously been modified.
// here's the source code lmao.
// you know were to find the GPL.

#include <stdint.h>

#include "rg_etc1.h"

/*
  compress image using etc1.
  input must be 32-bit 4ByPP.
  use Image::convertTo32(void).
*/

namespace rw {
namespace c3d {

int gTexQuality = rg_etc1::cLowQuality;

// Faint glass (all alpha < 128) rounds to nearest: flooring zeroes most of its texels.
static uint32_t
etc1Alpha4(uint8_t a, bool roundAlpha)
{
	return roundAlpha ? (a + 8) / 17 : (1<<4) * a / 256;
}
  
void
etc1_common(uint8_t *src, uint8_t **dst, int stride, bool alpha, bool roundAlpha)
{
	static bool ready = false;

	if (!ready){
		ready = true;
		rg_etc1::pack_etc1_block_init();
	}
	
	rg_etc1::etc1_pack_params params;

	params.clear();
	params.m_quality = gTexQuality; 

	for (int j = 0; j < 8; j += 4)
	{
		for (int i = 0; i < 8; i += 4)
		{
			uint8_t in_block[4 * 4 * 4];
			uint8_t out_block[8];
			uint8_t out_alpha[8] = {0, 0, 0, 0, 0, 0, 0, 0};

			// iterate each 4x4 subblock
			for (int y = 0; y < 4; ++y)
			{
				for (int x = 0; x < 4; ++x)
				{
					uint8_t *pix = src +
						((7 - (j + y)) * stride) + /* my code is beautiful */
						((i + x) * 4); /* good thing I'm not a professional */
				
					in_block[y * 16 + x * 4 + 0] = pix[0];
					in_block[y * 16 + x * 4 + 1] = pix[1];
					in_block[y * 16 + x * 4 + 2] = pix[2];
					in_block[y * 16 + x * 4 + 3] = 0xFF;

					if (alpha)
					{
						uint32_t a4 = etc1Alpha4(pix[3], roundAlpha);
						// encode 4bpp alpha; X/Y axes are swapped
						if (y & 1){
							out_alpha[2 * x + y / 2] |= (a4 << 4);
						}else{
							out_alpha[2 * x + y / 2] |= (a4 << 0);
						}
					}
				}
			}

			// encode etc1 block
			rg_etc1::pack_etc1_block
				(out_block, reinterpret_cast<unsigned int*> (in_block), params);

			// alpha block precedes etc1 block
			if(alpha){
				for (int i = 0; i < 8; ++i){
					*((*dst)++) = out_alpha[i]; // intentionally hard to read
				}
			}
		
			// rg_etc1 outputs in big-endian; convert to little-endian
			for (int i = 0; i < 8; i++){
				*((*dst)++) = out_block[8 - i - 1]; // lol
			}
		}
	}
}

/* Inverse of etc1_common for one 8x8 tile. Alpha nibble n decodes to n*17,
 * as on the GPU. */
static void
etc1_decode_common(const uint8_t **src, uint8_t *dst, int stride, bool alpha)
{
	for (int j = 0; j < 8; j += 4)
	{
		for (int i = 0; i < 8; i += 4)
		{
			const uint8_t *in_alpha = *src;
			if (alpha)
				*src += 8;

			uint8_t in_block[8];
			for (int k = 0; k < 8; k++)
				in_block[k] = (*src)[8 - k - 1];
			*src += 8;

			unsigned int out_block[4 * 4];
			rg_etc1::unpack_etc1_block(in_block, out_block);

			for (int y = 0; y < 4; ++y)
			{
				for (int x = 0; x < 4; ++x)
				{
					uint8_t *pix = dst + ((7 - (j + y)) * stride) + ((i + x) * 4);
					const uint8_t *rgba = reinterpret_cast<const uint8_t*>(&out_block[y * 4 + x]);
					pix[0] = rgba[0];
					pix[1] = rgba[1];
					pix[2] = rgba[2];
					if (alpha){
						uint8_t packed = in_alpha[2 * x + y / 2];
						pix[3] = 17 * ((y & 1) ? packed >> 4 : packed & 0xF);
					}else{
						pix[3] = 0xFF;
					}
				}
			}
		}
	}
}

/* Decode one ETC1 or ETC1A4 level into 32-bit RGBA, in the image layout that
 * texCompress reads (stride width*4). */
void
etc1_decode(const uint8_t *src, uint8_t *dst, int width, int height, bool alpha)
{
	const int stride = width * 4;
	for (int y = height - 8; y >= 0; y -= 8)
		for (int x = 0; x < width; x += 8)
			etc1_decode_common(&src, &dst[(x * 4) + (y * stride)], stride, alpha);
}

/* Halve a 32-bit RGBA image. Each output texel is the rounded mean of a 2x2
 * block of input texels. */
void
boxDownsample2x(const uint8_t *src, uint8_t *dst, int width, int height)
{
	const int stride = width * 4;
	for (int y = 0; y < height / 2; y++)
		for (int x = 0; x < width / 2; x++)
			for (int c = 0; c < 4; c++){
				const uint8_t *p = src + (2 * y) * stride + (2 * x) * 4 + c;
				*dst++ = (p[0] + p[4] + p[stride] + p[stride + 4] + 2) / 4;
			}
}

}
}
