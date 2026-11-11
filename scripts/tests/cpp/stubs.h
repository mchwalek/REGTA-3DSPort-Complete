// Minimal stand-ins for common reLCS engine types, shared by the host-compiled
// tests in scripts/tests/. Only add what more than one harness needs.
#pragma once
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>

typedef int8_t int8;
typedef uint8_t uint8;
typedef int16_t int16;
typedef uint16_t uint16;
typedef int32_t int32;
typedef uint32_t uint32;
typedef uint16_t wchar;
#define nil NULL

#define PI 3.14159265358979323846f
#define DEGTORAD(x) ((x) * PI / 180.0f)
#define RADTODEG(x) ((x) * 180.0f / PI)

static inline float Abs(float v) { return fabsf(v); }
static inline float Sin(float v) { return sinf(v); }
static inline float Cos(float v) { return cosf(v); }
static inline float Acos(float v) { return acosf(v); }
static inline float Sqrt(float v) { return sqrtf(v); }
static inline float Pow(float b, float e) { return powf(b, e); }
template<class T> static inline T Min(T a, T b) { return a < b ? a : b; }
template<class T> static inline T Max(T a, T b) { return a > b ? a : b; }
template<class T> static inline T Clamp(T v, T lo, T hi) { return v < lo ? lo : (v > hi ? hi : v); }

struct CVector {
	float x, y, z;
	CVector() : x(0.0f), y(0.0f), z(0.0f) {}
	CVector(float x, float y, float z) : x(x), y(y), z(z) {}
	CVector operator+(const CVector &v) const { return CVector(x + v.x, y + v.y, z + v.z); }
	CVector operator-(const CVector &v) const { return CVector(x - v.x, y - v.y, z - v.z); }
	CVector operator*(float f) const { return CVector(x * f, y * f, z * f); }
	float Magnitude() const { return sqrtf(x * x + y * y + z * z); }
	float Magnitude2D() const { return sqrtf(x * x + y * y); }
	void Normalise() { float m = Magnitude(); if (m > 1e-6f) { x /= m; y /= m; z /= m; } }
};

struct CVector2D {
	float x, y;
	CVector2D() : x(0.0f), y(0.0f) {}
	CVector2D(float x, float y) : x(x), y(y) {}
};

struct CRGBA {
	uint8 r, g, b, a;
	CRGBA() : r(0), g(0), b(0), a(255) {}
	CRGBA(uint8 r, uint8 g, uint8 b, uint8 a) : r(r), g(g), b(b), a(a) {}
};
