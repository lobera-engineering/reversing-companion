#include <stdio.h>
 
int main() {
    int a   = 67;
    int b   =  33;
 
    printf("var a = %d\n", a);
    printf("var b = %d\n\n", b);
    printf("  Complement of a = %d\n", ~a);
    printf("  a AND b = %d\n", a&b);
    printf("  a OR b =  %d\n", a|b);
    printf("  a XOR b = %d\n", a^b);
    printf("  A left shifted 1 = %d\n", a << 1);
    printf("  A right shifted 1 = %d\n", a >> 1);
    getchar();
    return 0;
    
}
