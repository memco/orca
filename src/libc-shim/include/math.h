#ifndef _MATH_H
#define _MATH_H

#ifdef __cplusplus
extern "C"
{
#endif

    // NOTE(orca): not doing anything fancy for float_t and double_t
    typedef float float_t;
    typedef double double_t;

#define NAN __builtin_nanf("")
#define INFINITY __builtin_inff()

#define FP_NAN 0
#define FP_INFINITE 1
#define FP_ZERO 2
#define FP_SUBNORMAL 3
#define FP_NORMAL 4

    int __fpclassify(double);
    int __fpclassifyf(float);
    int __fpclassifyl(long double);

    static __inline unsigned __FLOAT_BITS(float __f)
    {
        union
        {
            float __f;
            unsigned __i;
        } __u;

        __u.__f = __f;
        return __u.__i;
    }

    static __inline unsigned long long __DOUBLE_BITS(double __f)
    {
        union
        {
            double __f;
            unsigned long long __i;
        } __u;

        __u.__f = __f;
        return __u.__i;
    }

#define fpclassify(x) (                                                                           \
    sizeof(x) == sizeof(float) ? __fpclassifyf(x) : sizeof(x) == sizeof(double) ? __fpclassify(x) \
                                                                                : __fpclassifyl(x))

#define isinf(x) (                                                                                                                                              \
    sizeof(x) == sizeof(float) ? (__FLOAT_BITS(x) & 0x7fffffff) == 0x7f800000 : sizeof(x) == sizeof(double) ? (__DOUBLE_BITS(x) & -1ULL >> 1) == 0x7ffULL << 52 \
                                                                                                            : __fpclassifyl(x) == FP_INFINITE)

#define isnan(x) (                                                                                                                                            \
    sizeof(x) == sizeof(float) ? (__FLOAT_BITS(x) & 0x7fffffff) > 0x7f800000 : sizeof(x) == sizeof(double) ? (__DOUBLE_BITS(x) & -1ULL >> 1) > 0x7ffULL << 52 \
                                                                                                           : __fpclassifyl(x) == FP_NAN)

    double acos(double);

    double ceil(double);

    double cos(double);
    float cosf(float);

    double fabs(double);
    float fabsf(float);

    double floor(double);

    double fmod(double, double);

    double pow(double, double);

    double scalbn(double, int);

    double sin(double);
    float sinf(float);

    double sqrt(double);
    float sqrtf(float);

#define M_E 2.7182818284590452354         /* e */
#define M_LOG2E 1.4426950408889634074     /* log_2 e */
#define M_LOG10E 0.43429448190325182765   /* log_10 e */
#define M_LN2 0.69314718055994530942      /* log_e 2 */
#define M_LN10 2.30258509299404568402     /* log_e 10 */
#define M_PI 3.14159265358979323846       /* pi */
#define M_PI_2 1.57079632679489661923     /* pi/2 */
#define M_PI_4 0.78539816339744830962     /* pi/4 */
#define M_1_PI 0.31830988618379067154     /* 1/pi */
#define M_2_PI 0.63661977236758134308     /* 2/pi */
#define M_2_SQRTPI 1.12837916709551257390 /* 2/sqrt(pi) */
#define M_SQRT2 1.41421356237309504880    /* sqrt(2) */
#define M_SQRT1_2 0.70710678118654752440  /* 1/sqrt(2) */

#ifdef __cplusplus
}
#endif

#endif
